"""Lightweight civic-complaint duplicate signals for images, places, and text."""

import hashlib
import io
import math
import re
from collections import Counter
from difflib import SequenceMatcher

from PIL import Image, ImageOps


SYNONYMS = {
    "potholes": "pothole",
    "crater": "pothole",
    "craters": "pothole",
    "holes": "hole",
    "roadway": "road",
    "roads": "road",
    "street": "road",
    "streets": "road",
    "rubbish": "garbage",
    "trash": "garbage",
    "litter": "garbage",
    "waste": "garbage",
    "drains": "drain",
    "drainage": "drain",
    "blocked": "blockage",
    "clogged": "blockage",
    "flooding": "waterlogging",
    "flooded": "waterlogging",
    "streetlight": "light",
    "streetlights": "light",
    "lamps": "light",
}
STOP_WORDS = {"a", "an", "and", "at", "by", "for", "in", "is", "near", "of", "on", "the", "to", "with"}
CATEGORY_GROUPS = {
    "pothole": "road_damage",
    "road damage": "road_damage",
    "road_damage": "road_damage",
    "road obstruction": "road_damage",
    "road_obstruction": "road_damage",
    "garbage / waste": "garbage",
    "garbage/waste": "garbage",
    "garbage": "garbage",
    "drainage": "drainage",
    "water logging": "drainage",
    "water_logging": "drainage",
    "waterlogging": "drainage",
}


def image_fingerprints(image_bytes: bytes) -> tuple[str, str] | None:
    """Return exact SHA-256 and 64-bit difference hash for a readable image."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("L").resize((9, 8))
            pixels = list(image.getdata())
    except (OSError, ValueError):
        return None

    bits = 0
    for row in range(8):
        for column in range(8):
            bits = (bits << 1) | int(pixels[row * 9 + column] > pixels[row * 9 + column + 1])
    return hashlib.sha256(image_bytes).hexdigest(), f"{bits:016x}"


def image_hash_distance(left: str | None, right: str | None) -> int | None:
    if not left or not right:
        return None
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return None


def category_key(value: str | None) -> str:
    normalized = " ".join((value or "").lower().replace("/", " ").replace("_", " ").split())
    return CATEGORY_GROUPS.get(normalized, normalized)


def _tokens(value: str | None) -> Counter[str]:
    words = re.findall(r"[a-z0-9]+", (value or "").lower())
    normalized = [SYNONYMS.get(word, word) for word in words]
    return Counter(word for word in normalized if word not in STOP_WORDS)


def description_similarity(left: str | None, right: str | None) -> float:
    """Estimate similarity after normalizing common civic-issue synonyms."""
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0

    shared = set(left_tokens) & set(right_tokens)
    dot = sum(left_tokens[token] * right_tokens[token] for token in shared)
    left_norm = math.sqrt(sum(count * count for count in left_tokens.values()))
    right_norm = math.sqrt(sum(count * count for count in right_tokens.values()))
    cosine = dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
    sequence = SequenceMatcher(None, " ".join(left_tokens.elements()), " ".join(right_tokens.elements())).ratio()
    return max(cosine, sequence)


def distance_meters(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    earth_radius_meters = 6_371_000
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return earth_radius_meters * 2 * math.asin(math.sqrt(haversine))


def compare_complaint(candidate: dict, existing: dict) -> dict:
    """Return match signals and whether the existing issue should be shown as a warning."""
    exact_image = bool(
        candidate.get("sha256")
        and candidate.get("sha256") == existing.get("sha256")
    )
    hash_distance = image_hash_distance(
        candidate.get("perceptual_hash"), existing.get("perceptual_hash")
    )
    similar_image = hash_distance is not None and hash_distance <= 7
    same_category = bool(
        category_key(candidate.get("category"))
        and category_key(candidate.get("category")) == category_key(existing.get("category"))
    )
    text_similarity = description_similarity(
        candidate.get("description"), existing.get("description")
    )

    location_distance = None
    coordinates_present = all(
        value is not None
        for value in (
            candidate.get("latitude"), candidate.get("longitude"),
            existing.get("latitude"), existing.get("longitude"),
        )
    )
    if coordinates_present:
        location_distance = distance_meters(
            float(candidate["latitude"]), float(candidate["longitude"]),
            float(existing["latitude"]), float(existing["longitude"]),
        )
    candidate_location = " ".join((candidate.get("location") or "").lower().split())
    existing_location = " ".join((existing.get("location") or "").lower().split())
    same_location_text = bool(
        candidate_location
        and existing_location
        and SequenceMatcher(None, candidate_location, existing_location).ratio() >= 0.82
    )
    nearby = (location_distance is not None and location_distance <= 200) or same_location_text

    reasons = []
    if exact_image:
        reasons.append("identical_image")
    elif similar_image:
        reasons.append("visually_similar_image")
    if same_category:
        reasons.append("same_category")
    if nearby:
        reasons.append("nearby_location")
    if text_similarity >= 0.45:
        reasons.append("similar_description")

    is_match = (
        exact_image
        or similar_image
        or (same_category and nearby)
        or (text_similarity >= 0.68 and (same_category or nearby))
        or (same_category and text_similarity >= 0.82)
    )
    score = (
        0.35 * int(same_category)
        + 0.35 * int(nearby)
        + 0.30 * min(text_similarity, 1.0)
        + (0.50 if exact_image else 0.25 if similar_image else 0.0)
    )
    return {
        "is_match": is_match,
        "score": round(min(score, 1.0), 3),
        "exact_image": exact_image,
        "similar_image": similar_image,
        "same_category": same_category,
        "nearby": nearby,
        "location_distance_meters": round(location_distance, 1) if location_distance is not None else None,
        "description_similarity": round(text_similarity, 3),
        "reasons": reasons,
    }
