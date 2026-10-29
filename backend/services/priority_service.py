"""
Priority assistance service.

Calculates a suggested priority for a complaint based on configurable factors.
This is a *heuristic* — not a scientifically validated risk prediction.
Officers can always override the suggested priority.
"""

# Weights for each factor (configurable)
WEIGHTS = {
    "safety_risk": 0.30,
    "road_obstruction": 0.20,
    "evidence_quality": 0.15,
    "ai_confidence": 0.15,
    "category_severity": 0.20,
}

# Categories ranked by typical severity (configurable)
CATEGORY_SEVERITY = {
    "pothole": 0.7,
    "road_damage": 0.7,
    "road_obstruction": 0.8,
    "waterlogging": 0.6,
    "drainage": 0.5,
    "garbage": 0.4,
    "streetlight": 0.5,
    "illegal_parking": 0.3,
    "sanitation": 0.4,
    "other": 0.3,
}

# Detection classes from YOLO that indicate safety risk
SAFETY_RISK_CLASSES = {"pothole", "fire", "person", "car", "truck", "bus"}

# Detection classes that indicate road obstruction
OBSTRUCTION_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}


def calculate_priority_score(
    category: str,
    ai_detections: list[dict] | None = None,
    has_video: bool = False,
    has_location: bool = False,
) -> dict:
    """
    Calculate a priority score from 0.0 to 1.0 and return a suggested priority level.

    Returns dict with:
      - score: float 0-1
      - priority: str (critical/high/medium/low/needs_review)
      - factors: dict of individual factor scores
      - explanation: str describing the calculation
    """
    factors = {}

    # 1. Category severity
    cat_key = category.lower().replace(" ", "_").replace("/", "_")
    factors["category_severity"] = CATEGORY_SEVERITY.get(cat_key, 0.3)

    # 2. Safety risk from AI detections
    safety_score = 0.0
    if ai_detections:
        safety_classes_found = [
            d for d in ai_detections
            if d.get("class", "").lower() in SAFETY_RISK_CLASSES
        ]
        if safety_classes_found:
            max_conf = max(d.get("confidence", 0) for d in safety_classes_found)
            safety_score = min(max_conf * 1.2, 1.0)  # slight boost
    factors["safety_risk"] = safety_score

    # 3. Road obstruction
    obstruction_score = 0.0
    if ai_detections:
        obstruction_found = [
            d for d in ai_detections
            if d.get("class", "").lower() in OBSTRUCTION_CLASSES
        ]
        if obstruction_found:
            obstruction_score = min(len(obstruction_found) * 0.25, 1.0)
    factors["road_obstruction"] = obstruction_score

    # 4. Evidence quality
    evidence_score = 0.3  # baseline
    if has_video:
        evidence_score += 0.4
    if has_location:
        evidence_score += 0.3
    factors["evidence_quality"] = min(evidence_score, 1.0)

    # 5. AI confidence (average)
    ai_conf = 0.0
    if ai_detections:
        confidences = [d.get("confidence", 0) for d in ai_detections]
        ai_conf = sum(confidences) / len(confidences) if confidences else 0
    factors["ai_confidence"] = ai_conf

    # Weighted score
    score = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)
    score = round(min(max(score, 0.0), 1.0), 3)

    # Map score to priority level
    if score >= 0.75:
        priority = "critical"
    elif score >= 0.55:
        priority = "high"
    elif score >= 0.35:
        priority = "medium"
    elif score >= 0.15:
        priority = "low"
    else:
        priority = "needs_review"

    # Explanation
    top_factor = max(factors, key=factors.get)
    explanation = (
        f"Priority score {score:.2f} → {priority}. "
        f"Strongest factor: {top_factor.replace('_', ' ')} ({factors[top_factor]:.2f}). "
        f"This is a heuristic suggestion — officers may override."
    )

    return {
        "score": score,
        "priority": priority,
        "factors": factors,
        "explanation": explanation,
    }
