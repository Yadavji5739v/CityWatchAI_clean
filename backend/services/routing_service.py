"""Department routing service — maps complaint category to the right department."""

# Default routing table: category → department name
# These are configurable; admins can change them via the departments table.
DEFAULT_ROUTING = {
    "pothole": "Road Maintenance",
    "crack": "Road Maintenance",
    "road_damage": "Road Maintenance",
    "road_obstruction": "Road Maintenance",
    "speed_breaker": "Road Maintenance",
    "manhole": "Drainage Department",
    "garbage": "Sanitation Department",
    "garbage_waste": "Sanitation Department",
    "waste_dumping": "Sanitation Department",
    "overflowing_bins": "Sanitation Department",
    "sanitation": "Sanitation Department",
    "streetlight": "Electrical & Public Lighting",
    "electrical_hazard": "Electrical & Public Lighting",
    "traffic_signal": "Electrical & Public Lighting",
    "drainage": "Drainage Department",
    "poor_drainage": "Drainage Department",
    "water_logging": "Drainage Department",
    "waterlogging": "Drainage Department",
    "sewage": "Drainage Department",
    "flooding": "Drainage Department",
    "illegal_parking": "Traffic & Parking",
    "traffic_violation": "Traffic & Parking",
    "road_safety": "Traffic & Parking",
}

DEPARTMENT_NAME_ALIASES = {
    "Road Maintenance": {"road maintenance", "roads & public works", "road department"},
    "Sanitation Department": {"sanitation department"},
    "Electrical & Public Lighting": {
        "electrical & public lighting",
        "electrical maintenance department",
    },
    "Drainage Department": {"drainage department", "water department"},
    "Traffic & Parking": {"traffic & parking", "traffic department"},
}


def suggest_department(category: str, departments: list[dict]) -> dict | None:
    """
    Given a complaint category and a list of department records from the DB,
    return the best-matching department dict, or None if no match.

    First tries the DEFAULT_ROUTING lookup.
    Then falls back to scanning each department's issue_categories array.
    """
    category_lower = "_".join(category.lower().replace("/", " ").split())

    # Strategy 1: static routing table
    target_name = DEFAULT_ROUTING.get(category_lower)
    if target_name:
        accepted_names = DEPARTMENT_NAME_ALIASES.get(target_name, {target_name.lower()})
        for dept in departments:
            if (
                dept.get("name", "").strip().lower() in accepted_names
                and dept.get("is_active", True)
            ):
                return dept

    # Strategy 2: scan department issue_categories
    for dept in departments:
        cats = dept.get("issue_categories", [])
        if category_lower in [c.lower() for c in cats]:
            return dept

    # Strategy 3: return General Administration as fallback
    for dept in departments:
        if "general" in dept.get("name", "").lower():
            return dept

    return None


def find_routing_conflict(
    reported_category: str,
    predicted_category: str,
    departments: list[dict],
) -> tuple[dict, dict] | None:
    """Return the reported and predicted departments when their routing differs."""
    reported_department = suggest_department(reported_category, departments)
    predicted_department = suggest_department(predicted_category, departments)
    if (
        reported_department
        and predicted_department
        and reported_department["id"] != predicted_department["id"]
    ):
        return reported_department, predicted_department
    return None
