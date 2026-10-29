"""Valid status transitions for complaints."""

# Maps each status to the set of statuses it can transition to.
VALID_TRANSITIONS = {
    "submitted": {"ai_analysis", "pending_review", "rejected"},
    "ai_analysis": {"pending_review", "needs_information"},
    "pending_review": {"verified", "rejected", "needs_information"},
    "verified": {"assigned"},
    "assigned": {"in_progress", "pending_review"},
    "in_progress": {"resolved", "pending_review"},
    "resolved": {"closed", "reopened"},
    "closed": {"reopened"},
    "rejected": set(),  # terminal
    "reopened": {"pending_review", "assigned", "in_progress"},
    "needs_information": {"pending_review", "submitted", "rejected"},
}


def is_valid_transition(old_status: str, new_status: str) -> bool:
    """Check whether a status transition is permitted."""
    allowed = VALID_TRANSITIONS.get(old_status, set())
    return new_status in allowed


ALL_STATUSES = list(VALID_TRANSITIONS.keys())

PRIORITY_LEVELS = ["low", "medium", "high", "critical", "needs_review"]

CATEGORIES = [
    "pothole",
    "garbage",
    "illegal_parking",
    "road_obstruction",
    "road_damage",
    "waterlogging",
    "streetlight",
    "drainage",
    "other",
]
