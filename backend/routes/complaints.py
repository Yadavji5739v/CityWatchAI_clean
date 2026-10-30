
import os
import logging
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from database import UPLOAD_DIR, get_connection
from services.civic_classifier import classify_evidence
from services.local_auth import get_current_user
from services.routing_service import find_routing_conflict, suggest_department

router = APIRouter(prefix="/api", tags=["complaints"])
logger = logging.getLogger(__name__)

ALLOWED_EVIDENCE = {
    "video": {
        "extensions": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
        "mime_types": {
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/x-matroska",
            "video/webm",
        },
        "max_size": 50 * 1024 * 1024,
    },
    "image": {
        "extensions": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
        "mime_types": {"image/jpeg", "image/png", "image/webp", "image/gif"},
        "max_size": 10 * 1024 * 1024,
    },
}
MAX_VIDEO_SIZE_BYTES = int(os.getenv("CITYWATCH_MAX_VIDEO_SIZE_MB", "50")) * 1024 * 1024
MAX_IMAGE_COUNT = 5

COMPLAINT_SELECT = """
    SELECT c.*, d.name AS department,
           ai.analysis_status AS ai_analysis_status,
           ai.predicted_category AS ai_predicted_category,
           ai.confidence AS ai_confidence,
           ai.summary AS ai_summary
    FROM complaints c
    LEFT JOIN departments d ON d.id = c.assigned_department_id
    LEFT JOIN ai_analyses ai ON ai.id = (
        SELECT analysis.id FROM ai_analyses analysis
        WHERE analysis.complaint_id = c.id ORDER BY analysis.id DESC LIMIT 1
    )
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_complaint_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CW-{timestamp}-{suffix}"


def _serialize_complaint(row):
    if row is None:
        return None

    complaint = dict(row)
    complaint["date"] = complaint.get("created_at")
    complaint["location"] = complaint.get("location") or complaint.get("location_text") or ""
    complaint["location_text"] = complaint.get("location") or complaint.get("location_text") or ""
    complaint["video_url"] = (
        f"/api/complaints/{complaint['id']}/video"
        if complaint.get("video_path")
        else None
    )
    if complaint.get("ai_analysis_status"):
        complaint["ai_analysis"] = {
            "analysis_status": complaint["ai_analysis_status"],
            "predicted_category": complaint.get("ai_predicted_category"),
            "confidence": complaint.get("ai_confidence"),
            "summary": complaint.get("ai_summary"),
        }
    return complaint


async def _parse_complaint_request(request: Request):
    content_type = request.headers.get("content-type", "")
    payload = {}
    uploads = []

    if "multipart/form-data" in content_type:
        form = await request.form()
        payload = {
            "title": (form.get("title") or "").strip(),
            "category": (form.get("category") or "").strip(),
            "location": (form.get("location") or form.get("location_text") or "").strip(),
            "description": (form.get("description") or "").strip(),
            "priority": (form.get("priority") or "Needs Review").strip(),
            "status": (form.get("status") or "Submitted").strip(),
        }
        uploads.extend(
            file_obj
            for file_obj in (form.get("video"), *form.getlist("evidence"))
            if getattr(file_obj, "filename", None)
        )
    else:
        try:
            data = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Request body must be valid JSON or multipart form data.") from exc

        if isinstance(data, dict):
            payload = data
        else:
            raise HTTPException(status_code=400, detail="Request body must be JSON or multipart form data.")

    return payload, uploads


async def _save_uploaded_evidence(file_obj, user_id: str) -> dict:
    filename = Path(str(file_obj.filename)).name
    extension = Path(filename).suffix.lower()
    mime_type = (file_obj.content_type or "").lower()
    file_type = mime_type.split("/", 1)[0]
    configuration = ALLOWED_EVIDENCE.get(file_type)
    if not configuration or extension not in configuration["extensions"]:
        raise HTTPException(status_code=400, detail="Unsupported evidence file type.")
    if mime_type not in configuration["mime_types"]:
        raise HTTPException(status_code=400, detail="Unsupported evidence content type.")

    file_bytes = await file_obj.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded evidence file is empty.")

    maximum_size = configuration["max_size"]
    if file_type == "video":
        maximum_size = min(maximum_size, MAX_VIDEO_SIZE_BYTES)
    if len(file_bytes) > maximum_size:
        raise HTTPException(
            status_code=413,
            detail=f"{file_type.title()} exceeds the maximum allowed size of {maximum_size // (1024 * 1024)} MB.",
        )

    evidence_id = str(uuid.uuid4())
    safe_name = f"{evidence_id}{extension}"
    evidence_directory = UPLOAD_DIR / "evidence"
    evidence_directory.mkdir(parents=True, exist_ok=True)
    save_path = evidence_directory / safe_name
    save_path.write_bytes(file_bytes)
    return {
        "id": evidence_id,
        "original_name": filename,
        "file_type": file_type,
        "mime_type": mime_type,
        "file_size": len(file_bytes),
        "file_path": str(save_path.relative_to(Path(__file__).resolve().parent.parent).as_posix()),
        "path": save_path,
        "uploaded_by": user_id,
    }


@router.get("/complaints")
async def list_complaints(user: dict = Depends(get_current_user)):
    role = user["role"]
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            query = COMPLAINT_SELECT
            params = ()
            if role == "citizen":
                query += " WHERE c.created_by_user_id = %s"
                params = (user["id"],)
            elif role == "officer":
                query += """
                    WHERE (
                        LOWER(REPLACE(TRIM(c.status), '_', ' ')) IN ('submitted', 'pending review')
                    )
                       OR c.assigned_officer_id = %s
                       OR (
                           LOWER(TRIM(c.status)) = 'verified'
                           AND (
                               c.assigned_department_id = %s
                               OR (c.assigned_department_id IS NOT NULL AND %s IS NULL)
                           )
                       )
                """
                params = (user["id"], user.get("department_id"), user.get("department_id"))
            elif role != "admin":
                raise HTTPException(status_code=403, detail="Unauthorized.")
            query += " ORDER BY c.created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
        finally:
            cursor.close()

    return [_serialize_complaint(row) for row in rows]


@router.get("/complaints/my")
async def list_my_complaints(user: dict = Depends(get_current_user)):
    if user["role"] != "citizen":
        raise HTTPException(status_code=403, detail="Citizen access required.")
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                COMPLAINT_SELECT + """
                WHERE c.created_by_user_id = %s
                ORDER BY c.created_at DESC
                """,
                (user["id"],),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_serialize_complaint(row) for row in rows]


@router.get("/complaints/{complaint_id}")
async def get_complaint(complaint_id: str, user: dict = Depends(get_current_user)):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                COMPLAINT_SELECT + " WHERE c.id = %s",
                (complaint_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    if user["role"] == "citizen" and row.get("created_by_user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You can only view your own complaints.")
    if user["role"] == "officer":
        status_value = str(row["status"]).strip().lower().replace("_", " ")
        is_pending_review = status_value in {"submitted", "pending review"}
        is_routed_to_officer_department = (
            row.get("assigned_department_id") == user.get("department_id")
        )
        is_review_queue = is_pending_review and (
            not row.get("assigned_department_id") or is_routed_to_officer_department
        )
        is_approved_for_department = status_value == "verified" and is_routed_to_officer_department
        if (
            row.get("assigned_officer_id") != user["id"]
            and not is_review_queue
            and not is_approved_for_department
        ):
            raise HTTPException(status_code=403, detail="This complaint is not available to your account.")
    elif user["role"] not in {"citizen", "admin"}:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, original_name, file_type, file_size
                FROM evidence_files
                WHERE complaint_id = %s
                ORDER BY created_at
                """,
                (complaint_id,),
            )
            row["evidence_files"] = [
                {
                    **evidence,
                    "url": f"/api/complaints/{complaint_id}/evidence/{evidence['id']}",
                }
                for evidence in cursor.fetchall()
            ]
        finally:
            cursor.close()

    return _serialize_complaint(row)


@router.get("/complaints/{complaint_id}/video")
async def get_complaint_video(complaint_id: str, user: dict = Depends(get_current_user)):
    complaint = await get_complaint(complaint_id, user)
    if not complaint.get("video_path"):
        raise HTTPException(status_code=404, detail="No video evidence is attached to this complaint.")

    saved_path = Path(complaint["video_path"])
    resolved_path = saved_path if saved_path.is_absolute() else Path(__file__).resolve().parent.parent / saved_path
    try:
        resolved_path = resolved_path.resolve(strict=True)
        resolved_path.relative_to(UPLOAD_DIR.resolve())
    except (OSError, ValueError) as exc:
        logger.exception("Complaint evidence path is missing or outside the upload directory.")
        raise HTTPException(status_code=404, detail="Video evidence is unavailable.") from exc

    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Video evidence is unavailable.")

    content_type = mimetypes.guess_type(resolved_path.name)[0] or "application/octet-stream"
    return FileResponse(
        resolved_path,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{resolved_path.name}"'},
    )


@router.get("/complaints/{complaint_id}/evidence/{evidence_id}")
async def get_complaint_evidence(
    complaint_id: str,
    evidence_id: str,
    user: dict = Depends(get_current_user),
):
    await get_complaint(complaint_id, user)
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT original_name, mime_type, file_path
                FROM evidence_files
                WHERE id = %s AND complaint_id = %s
                """,
                (evidence_id, complaint_id),
            )
            evidence = cursor.fetchone()
        finally:
            cursor.close()

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence file not found.")

    saved_path = Path(evidence["file_path"])
    resolved_path = (
        saved_path
        if saved_path.is_absolute()
        else Path(__file__).resolve().parent.parent / saved_path
    )
    try:
        resolved_path = resolved_path.resolve(strict=True)
        resolved_path.relative_to(UPLOAD_DIR.resolve())
    except (OSError, ValueError) as exc:
        logger.exception("Complaint evidence path is missing or outside the upload directory.")
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.") from exc

    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.")
    return FileResponse(
        resolved_path,
        media_type=evidence["mime_type"],
        headers={"Content-Disposition": f'inline; filename="{Path(evidence["original_name"]).name}"'},
    )


class VerifyRequest(BaseModel):
    reason: str = Field(default="", max_length=1000)
    department_id: str = Field(min_length=1, max_length=36)


@router.post("/complaints/{complaint_id}/verify")
async def verify_complaint(
    complaint_id: str,
    request: VerifyRequest,
    user: dict = Depends(get_current_user),
):
    if user["role"] not in {"admin", "officer"}:
        raise HTTPException(status_code=403, detail="Only administrators and officers can verify complaints.")
    reason = request.reason.strip()

    with get_connection() as connection:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT status FROM complaints WHERE id = %s FOR UPDATE", (complaint_id,))
            complaint = cursor.fetchone()
            if not complaint:
                raise HTTPException(status_code=404, detail="Complaint not found.")
            review_status = str(complaint["status"]).strip().lower().replace("_", " ")
            if review_status not in {"submitted", "pending review"}:
                raise HTTPException(
                    status_code=409,
                    detail="Only submitted or pending-review complaints can be verified.",
                )

            cursor.execute(
                "SELECT id, name FROM departments WHERE id = %s AND is_active = 1",
                (request.department_id,),
            )
            department = cursor.fetchone()
            if not department:
                raise HTTPException(status_code=422, detail="Select an active department.")

            now = datetime.now(timezone.utc)
            cursor.execute(
                """
                UPDATE complaints
                SET status = 'Verified', assigned_department_id = %s, updated_at = %s
                WHERE id = %s
                """,
                (request.department_id, now.isoformat(), complaint_id),
            )
            cursor.execute(
                """
                INSERT INTO complaint_history
                    (complaint_id, actor_id, old_status, new_status, action, reason, metadata, created_at)
                VALUES (%s, %s, %s, 'Verified', 'verified', %s, %s, %s)
                """,
                (
                    complaint_id,
                    user["id"],
                    complaint["status"],
                    reason or None,
                    json.dumps({"department_id": department["id"], "department": department["name"]}),
                    now.replace(tzinfo=None),
                ),
            )
            connection.commit()
        finally:
            cursor.close()
    return {
        "id": complaint_id,
        "status": "Verified",
        "assigned_department_id": department["id"],
        "department": department["name"],
        "department_name": department["name"],
    }


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
async def create_complaint(request: Request, user: dict = Depends(get_current_user)):
    if user["role"] != "citizen":
        raise HTTPException(status_code=403, detail="Only citizens can submit complaints.")
    payload, uploads = await _parse_complaint_request(request)

    title = str(payload.get("title") or "").strip()
    category = str(payload.get("category") or "").strip()
    location = str(payload.get("location") or "").strip() or str(payload.get("location_text") or "").strip()
    description = str(payload.get("description") or "").strip()
    priority = str(payload.get("priority") or "Needs Review").strip() or "Needs Review"
    complaint_status = "Pending Review"

    if not title or len(title) < 3:
        raise HTTPException(status_code=400, detail="Complaint title is required and must be at least 3 characters long.")
    if not category:
        raise HTTPException(status_code=400, detail="Complaint category is required.")
    if not description or len(description) < 5:
        raise HTTPException(status_code=400, detail="Complaint description is required and must be at least 5 characters long.")
    if not location:
        raise HTTPException(status_code=400, detail="The location of the reported issue is required.")


    complaint_id = _make_complaint_id()
    created_at = _utc_now()
    updated_at = created_at
    saved_evidence = []

    try:
        video_count = sum(1 for file_obj in uploads if (file_obj.content_type or "").startswith("video/"))
        image_count = sum(1 for file_obj in uploads if (file_obj.content_type or "").startswith("image/"))
        if video_count > 1:
            raise HTTPException(status_code=400, detail="Upload no more than one video.")
        if image_count > MAX_IMAGE_COUNT:
            raise HTTPException(status_code=400, detail=f"Upload no more than {MAX_IMAGE_COUNT} images.")

        for file_obj in uploads:
            saved_evidence.append(
                await _save_uploaded_evidence(file_obj, user["id"])
            )

        analysis_result = (
            await run_in_threadpool(classify_evidence, saved_evidence, category)
            if saved_evidence
            else {
                "analysis_status": "no_evidence",
                "model_name": "road_damage_5class_model",
                "predicted_category": None,
                "confidence": None,
                "predictions": [],
                "summary": "No evidence was uploaded; complaint left for human review.",
                "processing_time_ms": 0,
            }
        )
        routed_department = None
        if analysis_result.get("analysis_status") == "completed":
            with get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    cursor.execute(
                        "SELECT id, name, is_active FROM departments WHERE is_active = 1"
                    )
                    departments = cursor.fetchall()
                    routed_department = suggest_department(
                        analysis_result["predicted_category"], departments
                    )
                    routing_conflict = find_routing_conflict(
                        category,
                        analysis_result["predicted_category"],
                        departments,
                    )
                    if routing_conflict:
                        reported_department, predicted_department = routing_conflict
                        routed_department = None
                        analysis_result["analysis_status"] = "review_required"
                        analysis_result["summary"] = (
                            f"The model predicted {analysis_result['predicted_category']} "
                            f"({analysis_result.get('confidence', 0):.1%}), which maps to "
                            f"{predicted_department['name']}, but the reported category "
                            f"{category} maps to {reported_department['name']}. "
                            "Automatic routing was skipped; staff review is required."
                        )
                finally:
                    cursor.close()

        first_video = next(
            (item for item in saved_evidence if item["file_type"] == "video"),
            None,
        )
        video_name = first_video["original_name"] if first_video else None
        video_path = first_video["file_path"] if first_video else None
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        with get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    """
                    INSERT INTO complaints (
                        id, title, category, location, description,
                        video_name, video_path, priority, status, created_at, updated_at,
                        created_by_user_id, assigned_department_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        complaint_id,
                        title,
                        category,
                        location,
                        description,
                        video_name,
                        video_path,
                        priority,
                        complaint_status,
                        created_at,
                        updated_at,
                        user["id"],
                        routed_department["id"] if routed_department else None,
                    ),
                )
                for evidence_item in saved_evidence:
                    cursor.execute(
                        """
                        INSERT INTO evidence_files (
                            id, complaint_id, original_name, file_type, mime_type,
                            file_size, file_path, uploaded_by, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            evidence_item["id"],
                            complaint_id,
                            evidence_item["original_name"],
                            evidence_item["file_type"],
                            evidence_item["mime_type"],
                            evidence_item["file_size"],
                            evidence_item["file_path"],
                            user["id"],
                            now,
                        ),
                    )
                cursor.execute(
                    """
                    INSERT INTO ai_analyses (
                        complaint_id, model_name, model_version, analysis_status,
                        predicted_category, confidence, predictions, summary,
                        error_message, processing_time_ms, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        complaint_id,
                        analysis_result["model_name"],
                        analysis_result.get("model_version"),
                        analysis_result["analysis_status"],
                        analysis_result.get("predicted_category"),
                        analysis_result.get("confidence"),
                        json.dumps(analysis_result.get("predictions", [])),
                        analysis_result["summary"],
                        analysis_result.get("error_message"),
                        analysis_result.get("processing_time_ms", 0),
                        now,
                    ),
                )
                cursor.execute(COMPLAINT_SELECT + " WHERE c.id = %s", (complaint_id,))
                row = cursor.fetchone()
                cursor.execute(
                    """
                    INSERT INTO complaint_history
                        (complaint_id, actor_id, old_status, new_status, action, created_at)
                    VALUES (%s, %s, NULL, %s, 'submitted', %s)
                    """,
                    (complaint_id, user["id"], complaint_status, now),
                )
                if routed_department:
                    cursor.execute(
                        """
                        INSERT INTO complaint_history
                            (complaint_id, actor_id, old_status, new_status, action, reason, metadata, created_at)
                        VALUES (%s, %s, %s, %s, 'ai_department_routed', %s, %s, %s)
                        """,
                        (
                            complaint_id,
                            user["id"],
                            complaint_status,
                            complaint_status,
                            f"Model classified evidence as {analysis_result['predicted_category']}.",
                            json.dumps({
                                "department_id": routed_department["id"],
                                "department_name": routed_department["name"],
                                "confidence": analysis_result["confidence"],
                            }),
                            now,
                        ),
                    )
            finally:
                cursor.close()
    except HTTPException:
        for evidence_item in saved_evidence:
            try:
                evidence_item["path"].unlink(missing_ok=True)
            except OSError:
                logger.exception("Unable to remove evidence after complaint submission failure.")
        raise
    except Exception as exc:
        for evidence_item in saved_evidence:
            try:
                evidence_item["path"].unlink(missing_ok=True)
            except OSError:
                logger.exception("Unable to remove evidence after complaint save failure.")
        logger.exception("Unable to save complaint %s.", complaint_id, exc_info=exc)
        raise HTTPException(status_code=500, detail="Unable to save complaint.") from exc

    complaint = _serialize_complaint(row)
    complaint["evidence_files"] = [
        {
            "id": item["id"],
            "original_name": item["original_name"],
            "file_type": item["file_type"],
            "file_size": item["file_size"],
            "url": f"/api/complaints/{complaint_id}/evidence/{item['id']}",
        }
        for item in saved_evidence
    ]
    complaint["ai_analysis"] = analysis_result
    return complaint


@router.get("/complaints/{complaint_id}/details")
async def complaint_details(complaint_id: str, user: dict = Depends(get_current_user)):
    return await get_complaint(complaint_id, user)
