import pytest
from fastapi import HTTPException
from PIL import Image, ImageDraw

from services.duplicate_detection import (
    compare_complaint,
    image_fingerprints,
)
from routes.complaints import _validate_duplicate_choice


def _sample_image(color="gray"):
    image = Image.new("RGB", (40, 40), color=color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 30, 30), fill="black")
    buffer = __import__("io").BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_identical_image_is_detected_independent_of_filename():
    first_upload = _sample_image()
    second_upload = bytes(first_upload)
    first_hashes = image_fingerprints(first_upload)
    second_hashes = image_fingerprints(second_upload)

    match = compare_complaint(
        {"sha256": first_hashes[0], "perceptual_hash": first_hashes[1]},
        {"sha256": second_hashes[0], "perceptual_hash": second_hashes[1]},
    )

    assert match["is_match"]
    assert match["exact_image"]
    assert "identical_image" in match["reasons"]


def test_matching_category_nearby_location_and_description_is_detected():
    match = compare_complaint(
        {
            "category": "Pothole",
            "location": "Main Road near school",
            "latitude": 30.75,
            "longitude": 76.65,
            "description": "A deep pothole blocks the road near the school entrance.",
        },
        {
            "category": "Road Damage",
            "location": "Main Road near school",
            "latitude": 30.7501,
            "longitude": 76.6501,
            "description": "Deep road crater near school entrance blocks traffic.",
        },
    )

    assert match["is_match"]
    assert match["same_category"]
    assert match["nearby"]
    assert "similar_description" in match["reasons"]


def test_visual_similarity_can_warn_without_auto_merge():
    fingerprints = image_fingerprints(_sample_image())
    match = compare_complaint(
        {"perceptual_hash": fingerprints[1]},
        {"perceptual_hash": fingerprints[1]},
    )

    assert match["is_match"]
    assert match["similar_image"]
    assert match["reasons"] == ["visually_similar_image"]


def test_server_requires_explicit_new_complaint_confirmation_for_matches():
    matches = [{"id": "CW-existing", "title": "Existing report"}]
    with pytest.raises(HTTPException) as error:
        _validate_duplicate_choice(matches, None, False)
    assert error.value.status_code == 409
    assert error.value.detail["code"] == "duplicate_confirmation_required"
    assert error.value.detail["matches"] == matches


def test_server_accepts_explicit_new_complaint_or_valid_support_choice():
    matches = [{"id": "CW-existing"}]
    assert _validate_duplicate_choice(matches, None, True) is None
    assert _validate_duplicate_choice(matches, "CW-existing", False) == "CW-existing"
