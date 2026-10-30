<<<<<<< HEAD

"""MySQL-backed complaint assignment, progress, and notification routes."""
=======
"""PostgreSQL-backed complaint assignment, progress, and notification routes."""
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from database import get_connection
from services.local_auth import get_current_user


router = APIRouter(prefix="/api", tags=["assignments"])


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class AssignmentRequest(BaseModel):
    department_id: str = Field(min_length=1, max_length=36)
    officer_id: str = Field(min_length=3, max_length=40)
    priority: str = Field(default="Medium", min_length=1, max_length=50)
    reassignment_reason: Optional[str] = Field(
        default=None, max_length=1000
    )


class ProgressRequest(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    note: Optional[str] = Field(default=None, max_length=2000)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def _require_role(user: dict, roles: set[str]) -> None:
    if user["role"] not in roles:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to perform this action."
        )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------
# GET ACTIVE DEPARTMENTS
# ---------------------------------------------------------

@router.get("/departments")
def list_departments(
    user: dict = Depends(get_current_user)
):
    _require_role(user, {"admin", "officer"})

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id, name
                FROM departments
                WHERE is_active = 1
                ORDER BY name
            """)

            return cursor.fetchall()

        finally:
            cursor.close()


# ---------------------------------------------------------
# GET OFFICERS BY DEPARTMENT
# ---------------------------------------------------------

@router.get("/officers")
def list_eligible_officers(
    department_id: str = Query(min_length=1, max_length=36),
    user: dict = Depends(get_current_user)
):
    _require_role(user, {"admin"})

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT
                    u.id,
                    u.full_name,
                    u.department_id,
                    d.name AS department_name
                FROM users u
                JOIN departments d
                    ON d.id = u.department_id
                WHERE
                    u.role = 'officer'
                    AND u.is_active = 1
                    AND d.is_active = 1
                    AND u.department_id = %s
                ORDER BY u.full_name
            """, (department_id,))

            return cursor.fetchall()

        finally:
            cursor.close()


# ---------------------------------------------------------
# GET ASSIGNMENTS
# ---------------------------------------------------------

@router.get("/assignments")
def get_assignments(
    user: dict = Depends(get_current_user)
):
    _require_role(user, {"admin", "officer"})

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            query = """
<<<<<<< HEAD
                SELECT
                    a.id AS assignment_id,
                    a.complaint_id,
                    c.title,
                    c.category,
                    c.location,
                    c.priority,
                    c.status,
                    a.assigned_at,

                    NULL AS due_date,
                    NULL AS instructions,

                    a.department_id,
                    d.name AS department_name,
                    a.officer_id,
                    u.full_name AS officer_name,
                    a.assigned_by,
                    a.reassignment_reason,
                    0 AS department_queue

=======
                SELECT a.id AS assignment_id, a.complaint_id, c.title,
                       c.category, c.location, c.latitude, c.longitude,
                       c.priority, c.status, a.assigned_at::text AS assigned_at, a.due_date,
                       a.instructions, a.department_id, d.name AS department_name,
                       a.officer_id, u.full_name AS officer_name, a.assigned_by,
                       a.reassignment_reason, 0 AS department_queue
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
                FROM assignments a

                JOIN complaints c
                    ON c.id = a.complaint_id

                JOIN departments d
                    ON d.id = a.department_id

                JOIN users u
                    ON u.id = a.officer_id

                WHERE a.is_active = 1
            """

            parameters = ()

            # Officer sees their own assignments and eligible
            # unassigned complaints in their department.
            if user["role"] == "officer":

                query += " AND a.officer_id = %s"
                parameters = (user["id"],)

                query += """
                    UNION ALL

                    SELECT
                        CONCAT('department-', c.id) AS assignment_id,
                        c.id AS complaint_id,
                        c.title,
                        c.category,
                        c.location,
                        c.priority,
                        c.status,
                        c.updated_at AS assigned_at,

                        NULL AS due_date,
                        NULL AS instructions,

                        d.id AS department_id,
                        d.name AS department_name,
                        NULL AS officer_id,
                        NULL AS officer_name,
                        NULL AS assigned_by,
                        NULL AS reassignment_reason,
                        1 AS department_queue

                    FROM complaints c

                    JOIN departments d
                        ON d.id = c.assigned_department_id

                    JOIN ai_analyses ai
                        ON ai.id = (
                            SELECT analysis.id
                            FROM ai_analyses analysis
                            WHERE analysis.complaint_id = c.id
                            ORDER BY analysis.id DESC
                            LIMIT 1
                        )

                    WHERE
                        LOWER(
                            REPLACE(TRIM(c.status), '_', ' ')
                        ) = 'pending review'

                        AND d.id = %s

                        AND LOWER(TRIM(ai.analysis_status)) = 'completed'

                        AND NOT EXISTS (
                            SELECT 1
                            FROM assignments active_assignment
                            WHERE
                                active_assignment.complaint_id = c.id
                                AND active_assignment.is_active = 1
                        )
                """

                parameters += (user.get("department_id"),)

            query += " ORDER BY assigned_at DESC"

            cursor.execute(query, parameters)

            return cursor.fetchall()

        finally:
            cursor.close()


# ---------------------------------------------------------
# ASSIGN COMPLAINT TO OFFICER
# ---------------------------------------------------------

@router.post(
    "/complaints/{complaint_id}/assign",
    status_code=status.HTTP_201_CREATED
)
def assign_complaint(
    complaint_id: str,
    request: AssignmentRequest,
    user: dict = Depends(get_current_user)
):
    _require_role(user, {"admin"})

    priority = request.priority.strip()

    if priority.lower() not in {
        "low", "medium", "high", "critical"
    }:
        raise HTTPException(
            status_code=422,
            detail="Choose a valid priority."
        )

    with get_connection() as connection:

        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        try:

            # 1. Check complaint
            cursor.execute("""
                SELECT id, status
                FROM complaints
                WHERE id = %s
                FOR UPDATE
            """, (complaint_id,))

            complaint = cursor.fetchone()

            if not complaint:
                raise HTTPException(
                    status_code=404,
                    detail="Complaint not found."
                )

            old_status = complaint["status"]

            normalized_status = (
                str(old_status)
                .strip()
                .lower()
                .replace("_", " ")
            )

            if normalized_status not in {
                "verified", "assigned", "in progress"
            }:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Only verified complaints can be assigned. "
                        "Verify this complaint first."
                    )
                )

            # 2. Validate department
            cursor.execute("""
                SELECT id
                FROM departments
                WHERE id = %s AND is_active = 1
            """, (request.department_id,))

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=422,
                    detail="Selected department is not active."
                )

<<<<<<< HEAD
            # 3. Validate officer
            cursor.execute("""
                SELECT id
                FROM users
                WHERE
                    id = %s
                    AND role = 'officer'
                    AND department_id = %s
                    AND is_active = 1
            """, (
                request.officer_id,
                request.department_id
            ))

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Select an active officer assigned "
                        "to the selected department."
                    )
                )

            # 4. Check existing active assignment
            cursor.execute("""
                SELECT id, officer_id, department_id
                FROM assignments
                WHERE
                    complaint_id = %s
                    AND is_active = 1
                FOR UPDATE
            """, (complaint_id,))

            active_assignment = cursor.fetchone()

=======
            cursor.execute(
                "SELECT canonical_complaint_id FROM complaint_supports WHERE supporting_complaint_id = %s",
                (complaint_id,),
            )
            support_link = cursor.fetchone()
            issue_root_id = support_link["canonical_complaint_id"] if support_link else complaint_id
            cursor.execute("SELECT id FROM complaints WHERE id = %s FOR UPDATE", (issue_root_id,))
            cursor.fetchone()
            cursor.execute(
                """
                SELECT a.id, a.complaint_id, a.officer_id, a.department_id
                FROM assignments a
                WHERE a.is_active = 1
                                    AND (
                                            a.complaint_id = %s
                                            OR a.complaint_id IN (
                                                    SELECT supporting_complaint_id
                                                    FROM complaint_supports
                                                    WHERE canonical_complaint_id = %s
                                            )
                                    )
                FOR UPDATE
                """,
                (issue_root_id, issue_root_id),
            )
            issue_assignments = cursor.fetchall()
            active_assignment = next(
                (assignment for assignment in issue_assignments if assignment["complaint_id"] == complaint_id),
                None,
            )
            if any(assignment["complaint_id"] != complaint_id for assignment in issue_assignments):
                raise HTTPException(
                    status_code=409,
                    detail="This linked civic issue already has an active repair assignment.",
                )
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
            if active_assignment and (
                active_assignment["officer_id"] == request.officer_id
                and active_assignment["department_id"] == request.department_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This complaint is already assigned to that officer."
                )

            if active_assignment and not (
                request.reassignment_reason or ""
            ).strip():
                raise HTTPException(
                    status_code=422,
                    detail="A reason is required when reassigning a complaint."
                )

            # 5. Deactivate previous assignment
            if active_assignment:

                cursor.execute("""
                    UPDATE assignments
                    SET is_active = 0
                    WHERE id = %s
                """, (active_assignment["id"],))

            # 6. Create new assignment
            assignment_id = str(uuid.uuid4())
            assigned_at = _now()

            cursor.execute("""
                INSERT INTO assignments (
                    id,
                    complaint_id,
                    department_id,
                    officer_id,
                    assigned_by,
                    assigned_at,
                    reassignment_reason,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                assignment_id,
                complaint_id,
                request.department_id,
                request.officer_id,
                user["id"],
                assigned_at,
                (request.reassignment_reason or "").strip() or None
            ))

            # 7. Update complaint
            # No due_date or assignment_instructions columns required.
            new_status = "Assigned"

            cursor.execute("""
                UPDATE complaints
                SET
                    status = %s,
                    priority = %s,
                    assigned_department_id = %s,
                    assigned_officer_id = %s,
                    updated_at = %s
                WHERE id = %s
            """, (
                new_status,
                priority,
                request.department_id,
                request.officer_id,
                assigned_at,
                complaint_id
            ))

            # 8. Save complaint history
            cursor.execute("""
                INSERT INTO complaint_history (
                    complaint_id,
                    actor_id,
                    old_status,
                    new_status,
                    action,
                    reason,
                    metadata,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                complaint_id,
                user["id"],
                old_status,
                new_status,
                "reassigned" if active_assignment else "assigned",
                (request.reassignment_reason or "").strip() or None,
                json.dumps({
                    "department_id": request.department_id,
                    "officer_id": request.officer_id,
                    "assignment_id": assignment_id
                }),
                assigned_at
            ))

            # 9. Notify officer
            cursor.execute("""
                INSERT INTO notifications (
                    id,
                    recipient_id,
                    complaint_id,
                    title,
                    message,
                    is_read,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, 0, %s)
            """, (
                str(uuid.uuid4()),
                request.officer_id,
                complaint_id,
                "Complaint assigned to you",
                f"Complaint {complaint_id} has been assigned to your department.",
                assigned_at
            ))

            # 10. Get saved assignment
            cursor.execute("""
                SELECT
                    a.id AS assignment_id,
                    a.complaint_id,
                    a.officer_id,
                    u.full_name AS officer_name,
                    a.department_id,
                    d.name AS department_name,
                    a.assigned_at,

                    NULL AS due_date,
                    NULL AS instructions,

                    a.is_active

                FROM assignments a

                JOIN users u
                    ON u.id = a.officer_id

                JOIN departments d
                    ON d.id = a.department_id

                WHERE a.id = %s
            """, (assignment_id,))

            result = cursor.fetchone()

            connection.commit()

            return result

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()


# ---------------------------------------------------------
# UPDATE COMPLAINT PROGRESS
# ---------------------------------------------------------

@router.post("/complaints/{complaint_id}/progress")
def update_complaint_progress(
    complaint_id: str,
    request: ProgressRequest,
    user: dict = Depends(get_current_user)
):
    _require_role(user, {"officer"})

    requested_status = (
        request.status.strip()
        .lower()
        .replace("_", " ")
    )

    if requested_status not in {"in progress", "resolved"}:
        raise HTTPException(
            status_code=422,
            detail=(
                "Officers may set a complaint to "
                "In Progress or Resolved."
            )
        )

    with get_connection() as connection:

        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        try:

            # 1. Find complaint assigned to this officer
            cursor.execute("""
                SELECT
                    c.id,
                    c.status,
                    a.id AS assignment_id

                FROM complaints c

                JOIN assignments a
                    ON a.complaint_id = c.id
                    AND a.is_active = 1

                WHERE
                    c.id = %s
                    AND a.officer_id = %s

                FOR UPDATE
            """, (
                complaint_id,
                user["id"]
            ))

            complaint = cursor.fetchone()

            if not complaint:
                raise HTTPException(
                    status_code=404,
                    detail="Assigned complaint not found."
                )

            # 2. Validate status transition
            old_status = (
                str(complaint["status"])
                .strip()
                .lower()
                .replace("_", " ")
            )

            allowed_transitions = {
                "assigned": "in progress",
                "in progress": "resolved"
            }

            if allowed_transitions.get(old_status) != requested_status:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Invalid status transition from "
                        f"{complaint['status']} to {request.status}."
                    )
                )

            new_status = (
                "In Progress"
                if requested_status == "in progress"
                else "Resolved"
            )

            now = _now()

            # 3. Update only the complaint status
            cursor.execute("""
                UPDATE complaints
                SET
                    status = %s,
                    updated_at = %s
                WHERE id = %s
            """, (
                new_status,
                now,
                complaint_id
            ))

            # 4. Close assignment when resolved
            if requested_status == "resolved":

                cursor.execute("""
                    UPDATE assignments
                    SET is_active = 0
                    WHERE id = %s
                """, (complaint["assignment_id"],))

            # 5. Save progress history
            cursor.execute("""
                INSERT INTO complaint_history (
                    complaint_id,
                    actor_id,
                    old_status,
                    new_status,
                    action,
                    reason,
                    created_at
                )
                VALUES (%s, %s, %s, %s, 'progress_updated', %s, %s)
            """, (
                complaint_id,
                user["id"],
                complaint["status"],
                new_status,
                request.note,
                now
            ))

            connection.commit()

            return {
                "id": complaint_id,
                "status": new_status,
                "message": "Complaint progress updated successfully."
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()


# ---------------------------------------------------------
# GET NOTIFICATIONS
# ---------------------------------------------------------

@router.get("/notifications")
def get_notifications(
    user: dict = Depends(get_current_user)
):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT
                    id,
                    complaint_id,
                    title,
                    message,
                    is_read,
                    created_at

                FROM notifications

                WHERE recipient_id = %s

                ORDER BY created_at DESC

                LIMIT 50
            """, (user["id"],))

            return cursor.fetchall()

        finally:
            cursor.close()
