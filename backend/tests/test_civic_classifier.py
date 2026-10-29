import numpy as np
from PIL import Image

from services import civic_classifier
from services.routing_service import find_routing_conflict, suggest_department


class FakeModel:
    def __init__(self, scores):
        self.scores = np.asarray([scores], dtype=np.float32)

    def predict(self, image_tensor, **_kwargs):
        assert image_tensor.shape == (1, 224, 224, 3)
        return self.scores


def test_classifies_supported_image_and_maps_pothole(tmp_path, monkeypatch):
    image_path = tmp_path / "evidence.jpg"
    Image.new("RGB", (80, 40), color="gray").save(image_path)
    monkeypatch.setattr(
        civic_classifier,
        "_get_model",
        lambda: FakeModel([0.05, 0.05, 0.1, 0.1, 0.7]),
    )

    result = civic_classifier.classify_evidence(
        [{"path": str(image_path), "file_type": "image"}],
        "Pothole",
    )

    assert result["analysis_status"] == "completed"
    assert result["predicted_category"] == "pothole"
    assert result["confidence"] == 0.7
    assert result["predictions"][4]["class"] == "pothole"


def test_classifies_garbage_and_poor_drainage_using_five_class_model(tmp_path, monkeypatch):
    image_path = tmp_path / "evidence.jpg"
    Image.new("RGB", (80, 40), color="gray").save(image_path)
    monkeypatch.setattr(
        civic_classifier,
        "_get_model",
        lambda: FakeModel([0.05, 0.7, 0.05, 0.15, 0.05]),
    )

    garbage_result = civic_classifier.classify_evidence(
        [{"path": str(image_path), "file_type": "image"}],
        "Garbage / Waste",
    )
    assert garbage_result["analysis_status"] == "completed"
    assert garbage_result["predicted_category"] == "garbage"

    monkeypatch.setattr(
        civic_classifier,
        "_get_model",
        lambda: FakeModel([0.05, 0.15, 0.05, 0.7, 0.05]),
    )
    drainage_result = civic_classifier.classify_evidence(
        [{"path": str(image_path), "file_type": "image"}],
        "Drainage",
    )
    assert drainage_result["analysis_status"] == "completed"
    assert drainage_result["predicted_category"] == "poor_drainage"


def test_low_confidence_result_does_not_route(tmp_path, monkeypatch):
    image_path = tmp_path / "evidence.jpg"
    Image.new("RGB", (40, 40), color="gray").save(image_path)
    monkeypatch.setattr(
        civic_classifier,
        "_get_model",
        lambda: FakeModel([0.21, 0.20, 0.19, 0.20, 0.20]),
    )

    result = civic_classifier.classify_evidence(
        [{"path": str(image_path), "file_type": "image"}],
        "Road Damage",
    )

    assert result["analysis_status"] == "review_required"
    assert result["predicted_category"] is None
    assert result["confidence"] < civic_classifier.CONFIDENCE_THRESHOLD


def test_confidence_above_40_percent_is_classified(tmp_path, monkeypatch):
    image_path = tmp_path / "evidence.jpg"
    Image.new("RGB", (40, 40), color="gray").save(image_path)
    monkeypatch.setattr(
        civic_classifier,
        "_get_model",
        lambda: FakeModel([0.10, 0.10, 0.10, 0.25, 0.45]),
    )

    result = civic_classifier.classify_evidence(
        [{"path": str(image_path), "file_type": "image"}],
        "Road Damage",
    )

    assert civic_classifier.CONFIDENCE_THRESHOLD == 0.40
    assert result["analysis_status"] == "completed"
    assert result["predicted_category"] == "pothole"
    assert result["confidence"] == 0.45


def test_unsupported_report_category_is_not_classified(monkeypatch):
    def unexpected_model_load():
        raise AssertionError("Unsupported categories must not run the road classifier.")

    monkeypatch.setattr(civic_classifier, "_get_model", unexpected_model_load)
    result = civic_classifier.classify_evidence([], "Water Supply")

    assert result["analysis_status"] == "unsupported_category"
    assert result["predicted_category"] is None


def test_model_categories_route_to_seeded_departments():
    departments = [
        {"id": "roads", "name": "Roads & Public Works", "is_active": 1},
        {"id": "drainage", "name": "Drainage Department", "is_active": 1},
        {"id": "sanitation", "name": "Sanitation Department", "is_active": 1},
    ]

    assert suggest_department("pothole", departments)["id"] == "roads"
    assert suggest_department("manhole", departments)["id"] == "drainage"
    assert suggest_department("poor_drainage", departments)["id"] == "drainage"
    assert suggest_department("garbage", departments)["id"] == "sanitation"


def test_model_and_report_department_conflict_is_sent_for_manual_review():
    departments = [
        {"id": "roads", "name": "Roads & Public Works", "is_active": 1},
        {"id": "sanitation", "name": "Sanitation Department", "is_active": 1},
    ]

    conflict = find_routing_conflict("Pothole", "garbage", departments)

    assert conflict is not None
    reported_department, predicted_department = conflict
    assert reported_department["id"] == "roads"
    assert predicted_department["id"] == "sanitation"


def test_matching_report_and_model_department_has_no_routing_conflict():
    departments = [
        {"id": "roads", "name": "Roads & Public Works", "is_active": 1},
        {"id": "sanitation", "name": "Sanitation Department", "is_active": 1},
    ]

    assert find_routing_conflict("Road Damage", "pothole", departments) is None
