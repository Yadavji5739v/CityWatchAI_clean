"""MySQL-backed complaint assignment, progress, and notification routes."""

import json
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from database import get_connection
from services.local_auth import get_current_user

router = APIRouter(prefix="/api", tags=["assignments"])


class AssignmentRequest(BaseModel):
    department_id: str = Field(min_length=1, max_length=36)
    officer_id: str = Field(min_length=3, max_length=40)
    priority: str = Field(default="Medium", min_length=1, max_length=50)
    due_date: Optional[date] = None
    instructions: Optional[str] = Field(default=None, max_length=2000)
    reassignment_reason: Optional[str] = Field(default=None, max_length=1000)


class ProgressRequest(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    note: Optional[str] = Field(default=None, max_length=2000)


def _require_role(user: dict, roles: set[str]) -> None:
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="You are not authorized to perform this action.")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/departments")
def list_departments(user: dict = Depends(get_current_user)):
    _require_role(user, {"admin", "officer"})
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name FROM departments WHERE is_active = 1 ORDER BY name")
            return cursor.fetchall()
        finally:
            cursor.close()


@router.get("/officers")
def list_eligible_officers(
    department_id: str = Query(min_length=1, max_length=36),
    user: dict = Depends(get_current_user),
):
    _require_role(user, {"admin"})
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT u.id, u.full_name, u.department_id, d.name AS department_name
                FROM users u
                JOIN departments d ON d.id = u.department_id
                WHERE u.role = 'officer' AND u.is_active = 1
                  AND d.is_active = 1 AND u.department_id = %s
                ORDER BY u.full_name
                """,
                (department_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


@router.get("/assignments")
def get_assignments(user: dict = Depends(get_current_user)):
    _require_role(user, {"admin", "officer"})
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            query = """
                SELECT a.id AS assignment_id, a.complaint_id, c.title,
                       c.category, c.location, c.latitude, c.longitude,
                       c.priority, c.status, a.assigned_at, a.due_date,
                       a.instructions, a.department_id, d.name AS department_name,
                       a.officer_id, u.full_name AS officer_name, a.assigned_by,
                       a.reassignment_reason, 0 AS department_queue
                FROM assignments a
                JOIN complaints c ON c.id = a.complaint_id
                JOIN departments d ON d.id = a.department_id
                JOIN users u ON u.id = a.officer_id
                WHERE a.is_active = 1
            """
            parameters = ()
            if user["role"] == "officer":
                query += " AND a.officer_id = %s"
                parameters = (user["id"],)
                query += """
                    UNION ALL
                    SELECT CONCAT('department-', c.id) AS assignment_id, c.id AS complaint_id,
                           c.title, c.category, c.location, c.latitude, c.longitude,
                           c.priority, c.status, c.updated_at AS assigned_at,
                           NULL AS due_date, NULL AS instructions,
                           d.id AS department_id, d.name AS department_name,
                           NULL AS officer_id, NULL AS officer_name,
                           NULL AS assigned_by, NULL AS reassignment_reason,
                           1 AS department_queue
                    FROM complaints c
                    JOIN departments d ON d.id = c.assigned_department_id
                    JOIN ai_analyses ai ON ai.id = (
                        SELECT analysis.id FROM ai_analyses analysis
                        WHERE analysis.complaint_id = c.id
                        ORDER BY analysis.id DESC LIMIT 1
                    )
                    WHERE LOWER(REPLACE(TRIM(c.status), '_', ' ')) = 'pending review'
                      AND d.id = %s
                      AND LOWER(TRIM(ai.analysis_status)) = 'completed'
                      AND NOT EXISTS (
                          SELECT 1 FROM assignments active_assignment
                          WHERE active_assignment.complaint_id = c.id
                            AND active_assignment.is_active = 1
                      )
                """
                parameters += (user.get("department_id"),)
            query += " ORDER BY assigned_at DESC"
            cursor.execute(query, parameters)
            return cursor.fetchall()
        finally:
            cursor.close()


@router.post("/complaints/{complaint_id}/assign", status_code=status.HTTP_201_CREATED)
def assign_complaint(
    complaint_id: str,
    request: AssignmentRequest,
    user: dict = Depends(get_current_user),
):
    _require_role(user, {"admin"})
    priority = request.priority.strip()
    if priority.lower() not in {"low", "medium", "high", "critical"}:
        raise HTTPException(status_code=422, detail="Choose a valid priority.")

    with get_connection() as connection:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, status FROM complaints WHERE id = %s FOR UPDATE", (complaint_id,))
            complaint = cursor.fetchone()
            if not complaint:
                raise HTTPException(status_code=404, detail="Complaint not found.")

            old_status = complaint["status"]
            normalized_status = str(old_status).strip().lower().replace("_", " ")
            if normalized_status not in {"verified", "assigned", "in progress"}:
                raise HTTPException(
                    status_code=409,
                    detail="Only verified complaints can be assigned. Verify this complaint first.",
                )

            cursor.execute(
                "SELECT id FROM departments WHERE id = %s AND is_active = 1",
                (request.department_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=422, detail="Selected department is not active.")

            cursor.execute(
                """
                SELECT id FROM users
                WHERE id = %s AND role = 'officer' AND department_id = %s AND is_active = 1
                """,
                (request.officer_id, request.department_id),
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=422,
                    detail="Select an active officer assigned to the selected department.",
                )

            cursor.execute(
                """
                SELECT id, officer_id, department_id FROM assignments
                WHERE complaint_id = %s AND is_active = 1 FOR UPDATE
                """,
                (complaint_id,),
            )
            active_assignment = cursor.fetchone()
            if active_assignment and (
                active_assignment["officer_id"] == request.officer_id
                and active_assignment["department_id"] == request.department_id
            ):
                raise HTTPException(status_code=409, detail="This complaint is already assigned to that officer.")
            if active_assignment and not (request.reassignment_reason or "").strip():
                raise HTTPException(status_code=422, detail="A reason is required when reassigning a complaint.")

            if active_assignment:
                cursor.execute(
                    "UPDATE assignments SET is_active = 0 WHERE id = %s",
                    (active_assignment["id"],),
                )

            assignment_id = str(uuid.uuid4())
            assigned_at = _now()
            cursor.execute(
                """
                INSERT INTO assignments (
                    id, complaint_id, department_id, officer_id, assigned_by,
                    assigned_at, due_date, instructions, reassignment_reason, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                """,
                (
                    assignment_id,
                    complaint_id,
                    request.department_id,
                    request.officer_id,
                    user["id"],
                    assigned_at,
                    request.due_date,
                    (request.instructions or "").strip() or None,
                    (request.reassignment_reason or "").strip() or None,
                ),
            )

            new_status = "Assigned"
            cursor.execute(
                """
                UPDATE complaints
                SET status = %s, priority = %s, assigned_department_id = %s,
                    assigned_officer_id = %s, due_date = %s, assignment_instructions = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    new_status,
                    priority,
                    request.department_id,
                    request.officer_id,
                    request.due_date,
                    (request.instructions or "").strip() or None,
                    assigned_at.isoformat(),
                    complaint_id,
                ),
            )
            cursor.execute(
                """
                INSERT INTO complaint_history
                    (complaint_id, actor_id, old_status, new_status, action, reason, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    complaint_id,
                    user["id"],
                    old_status,
                    new_status,
                    "reassigned" if active_assignment else "assigned",
                    (request.reassignment_reason or "").strip() or None,
                    json.dumps({
                        "department_id": request.department_id,
                        "officer_id": request.officer_id,
                        "assignment_id": assignment_id,
                    }),
                    assigned_at,
                ),
            )
            cursor.execute(
                """
                INSERT INTO notifications (id, recipient_id, complaint_id, title, message, is_read, created_at)
                VALUES (%s, %s, %s, %s, %s, 0, %s)
                """,
                (
                    str(uuid.uuid4()),
                    request.officer_id,
                    complaint_id,
                    "Complaint assigned to you",
                    f"Complaint {complaint_id} has been assigned to your department.",
                    assigned_at,
                ),
            )
            cursor.execute(
                """
                SELECT a.id AS assignment_id, a.complaint_id, a.officer_id,
                       u.full_name AS officer_name, a.department_id,
                       d.name AS department_name, a.assigned_at, a.due_date,
                       a.instructions, a.is_active
                FROM assignments a
                JOIN users u ON u.id = a.officer_id
                JOIN departments d ON d.id = a.department_id
                WHERE a.id = %s
                """,
                (assignment_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


@router.post("/complaints/{complaint_id}/progress")
def update_complaint_progress(
    complaint_id: str,
    request: ProgressRequest,
    user: dict = Depends(get_current_user),
):
    _require_role(user, {"officer"})
    requested_status = request.status.strip().lower().replace("_", " ")
    if requested_status not in {"in progress", "resolved"}:
        raise HTTPException(status_code=422, detail="Officers may set a complaint to In Progress or Resolved.")

    with get_connection() as connection:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT c.id, c.status, a.id AS assignment_id
                FROM complaints c
                JOIN assignments a ON a.complaint_id = c.id AND a.is_active = 1
                WHERE c.id = %s AND a.officer_id = %s FOR UPDATE
                """,
                (complaint_id, user["id"]),
            )
            complaint = cursor.fetchone()
            if not complaint:
                raise HTTPException(status_code=404, detail="Assigned complaint not found.")

            old_status = str(complaint["status"]).strip().lower().replace("_", " ")
            allowed = {"assigned": "in progress", "in progress": "resolved"}
            if allowed.get(old_status) != requested_status:
                raise HTTPException(
                    status_code=409,
                    detail=f"Invalid status transition from {complaint['status']} to {request.status}.",
                )

            new_status = "In Progress" if requested_status == "in progress" else "Resolved"
            now = _now()
            cursor.execute(
                "UPDATE complaints SET status = %s, updated_at = %s WHERE id = %s",
                (new_status, now.isoformat(), complaint_id),
            )
            if requested_status == "resolved":
                cursor.execute(
                    "UPDATE assignments SET is_active = 0 WHERE id = %s",
                    (complaint["assignment_id"],),
                )
            cursor.execute(
                """
                INSERT INTO complaint_history
                    (complaint_id, actor_id, old_status, new_status, action, reason, created_at)
                VALUES (%s, %s, %s, %s, 'progress_updated', %s, %s)
                """,
                (complaint_id, user["id"], complaint["status"], new_status, request.note, now),
            )
            return {"id": complaint_id, "status": new_status}
        finally:
            cursor.close()


@router.get("/notifications")
def get_notifications(user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, complaint_id, title, message, is_read, created_at
                FROM notifications
                WHERE recipient_id = %s
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user["id"],),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
