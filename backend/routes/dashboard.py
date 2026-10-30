"""MySQL-backed role-specific dashboard statistics."""

from fastapi import APIRouter, Depends, HTTPException

from database import get_connection
from services.local_auth import get_current_user

router = APIRouter(prefix="/api", tags=["dashboards"])


@router.get("/dashboard/admin")
def admin_dashboard(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT COUNT(*) AS total_complaints,
                       SUM(CASE WHEN status IN ('Pending Review', 'Submitted', 'pending_review', 'submitted')
                                THEN 1 ELSE 0 END) AS pending_verification,
                       SUM(CASE WHEN status = 'Verified' AND assigned_officer_id IS NULL
                                THEN 1 ELSE 0 END) AS unassigned_complaints,
                       SUM(CASE WHEN status IN ('Assigned', 'In Progress')
                                THEN 1 ELSE 0 END) AS active_assignments,
                       SUM(CASE WHEN priority IN ('High', 'Critical', 'high', 'critical')
                                THEN 1 ELSE 0 END) AS high_priority,
                       SUM(CASE WHEN status IN ('Resolved', 'Closed', 'resolved', 'closed')
                                THEN 1 ELSE 0 END) AS resolved
                FROM complaints
                """
            )
            stats = cursor.fetchone()
            cursor.execute(
                """
                SELECT d.id, d.name, COUNT(a.id) AS active_assignments
                FROM departments d
                LEFT JOIN assignments a ON a.department_id = d.id AND a.is_active = 1
                WHERE d.is_active = 1
                GROUP BY d.id, d.name
                ORDER BY d.name
                """
            )
            department_workload = cursor.fetchall()
            cursor.execute(
                """
                SELECT u.id AS officer_id, u.full_name, d.name AS department_name,
                       COUNT(a.id) AS active_assignments
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                LEFT JOIN assignments a ON a.officer_id = u.id AND a.is_active = 1
                WHERE u.role = 'officer' AND u.is_active = 1
                GROUP BY u.id, u.full_name, d.name
                ORDER BY active_assignments DESC, u.full_name
                """
            )
            officer_workload = cursor.fetchall()
        finally:
            cursor.close()

    return {
        **{key: int(value or 0) for key, value in stats.items()},
        "department_workload": department_workload,
        "officer_workload": officer_workload,
    }


@router.get("/dashboard/officer")
def officer_dashboard(user: dict = Depends(get_current_user)):
    if user["role"] != "officer":
        raise HTTPException(status_code=403, detail="Officer access required.")

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT a.id AS assignment_id, a.complaint_id, c.title, c.category,
                       c.location, c.priority, c.status, a.assigned_at, a.due_date,
                       a.instructions, d.name AS department_name
                FROM assignments a
                JOIN complaints c ON c.id = a.complaint_id
                JOIN departments d ON d.id = a.department_id
                WHERE a.officer_id = %s AND a.is_active = 1
                ORDER BY a.assigned_at DESC
                """,
                (user["id"],),
            )
            assignments = cursor.fetchall()
            cursor.execute(
                """
                SELECT COUNT(*) AS new_complaints
                FROM complaints
                WHERE status IN ('Submitted', 'Pending Review', 'submitted', 'pending_review')
                """
            )
            new_count = cursor.fetchone()["new_complaints"]
        finally:
            cursor.close()

    return {
        "new_complaints": int(new_count or 0),
        "total_assigned": len(assignments),
        "active_assignments": sum(
            1 for assignment in assignments
            if assignment["status"] in {"Assigned", "In Progress"}
        ),
        "resolved": sum(
            1 for assignment in assignments
            if assignment["status"] in {"Resolved", "Closed"}
        ),
        "assigned_complaints": assignments,
    }


@router.get("/dashboard/citizen")
def citizen_dashboard(user: dict = Depends(get_current_user)):
    if user["role"] != "citizen":
        raise HTTPException(status_code=403, detail="Citizen access required.")

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM complaints WHERE created_by_user_id = %s
                GROUP BY status
                """,
                (user["id"],),
            )
            status_counts = {row["status"]: row["total"] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT id, title, category, status, priority, created_at
                FROM complaints WHERE created_by_user_id = %s
                ORDER BY created_at DESC LIMIT 5
                """,
                (user["id"],),
            )
            recent = cursor.fetchall()
        finally:
            cursor.close()

    normalized_counts = {str(status or "").strip().lower().replace("_", " "): int(total or 0)
                         for status, total in status_counts.items()}
    verified_statuses = {"verified", "assigned", "in progress", "resolved", "closed"}
    verified_reports = sum(count for status, count in normalized_counts.items() if status in verified_statuses)
    supported_reports = normalized_counts.get("supported", 0)
    return {
        "total_complaints": sum(status_counts.values()),
        "submitted": int(status_counts.get("Submitted", 0) + status_counts.get("Pending Review", 0)),
        "in_progress": int(status_counts.get("Assigned", 0) + status_counts.get("In Progress", 0)),
        "resolved": int(status_counts.get("Resolved", 0) + status_counts.get("Closed", 0)),
        "recent_complaints": recent,
        "status_breakdown": status_counts,
        "points": {
            "total": verified_reports * 20 + supported_reports * 5,
            "verified_reports": verified_reports,
            "supported_reports": supported_reports,
            "points_per_verified_report": 20,
            "points_per_supported_report": 5,
        },
    }
