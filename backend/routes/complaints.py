
import os
import logging
import json
import mimetypes
import base64
import uuid
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from database import UPLOAD_DIR, get_connection
from services.civic_classifier import classify_evidence
from services.duplicate_detection import compare_complaint, image_fingerprints
from services.local_auth import get_current_user
from services.routing_service import find_routing_conflict, suggest_department
from services.supabase_client import (
    delete_evidence,
    download_evidence,
    upload_evidence,
)

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
            "support_existing_id": (form.get("support_existing_id") or "").strip(),
            "confirm_new_complaint": (form.get("confirm_new_complaint") or "").strip().lower(),
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


async def _save_uploaded_evidence(file_obj, user_id: str, complaint_id: str) -> dict:
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

    fingerprints = image_fingerprints(file_bytes) if file_type == "image" else None

    evidence_id = str(uuid.uuid4())
    safe_name = f"{evidence_id}{extension}"
    storage_path = f"complaints/{complaint_id}/{evidence_id}{extension}"
    try:
        upload_evidence(storage_path, file_bytes, mime_type)
    except Exception as exc:
        logger.exception("Supabase evidence upload failed.")
        raise HTTPException(status_code=503, detail="Evidence storage is temporarily unavailable.") from exc

    # The temporary copy exists only while the classifier processes this request.
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(prefix="citywatch-evidence-", suffix=extension, delete=False) as temp_file:
            temp_file.write(file_bytes)
            processing_path = Path(temp_file.name)
    except Exception:
        try:
            delete_evidence(storage_path)
        except Exception:
            logger.exception("Unable to remove evidence after temporary processing-file creation failed.")
        raise
    return {
        "id": evidence_id,
        "original_name": filename,
        "file_type": file_type,
        "mime_type": mime_type,
        "file_size": len(file_bytes),
        "file_path": storage_path,
        "path": processing_path,
        "storage_path": storage_path,
        "uploaded_by": user_id,
        "sha256": fingerprints[0] if fingerprints else None,
        "perceptual_hash": fingerprints[1] if fingerprints else None,
    }


def _cleanup_uploaded_evidence(items: list[dict], *, delete_remote: bool) -> None:
    for item in items:
        path = item.get("path")
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                logger.exception("Unable to remove temporary evidence file.")
        if delete_remote and item.get("storage_path"):
            try:
                delete_evidence(item["storage_path"])
            except Exception:
                logger.exception("Unable to remove evidence after a failed complaint save.")


def _image_preview_data(source: Path | bytes) -> str | None:
    try:
        image_source = Image.open(BytesIO(source)) if isinstance(source, bytes) else Image.open(source)
        with image_source as opened_image:
            image = ImageOps.exif_transpose(opened_image).convert("RGB")
            image.thumbnail((480, 360))
            output = BytesIO()
            image.save(output, format="JPEG", quality=76, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
    except (OSError, ValueError):
        logger.warning("Unable to create duplicate-match preview.")
        return None


def _local_evidence_path(stored_path: str) -> Path | None:
    path = Path(stored_path)
    candidate = path if path.is_absolute() else Path(__file__).resolve().parent.parent / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(UPLOAD_DIR.resolve())
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _find_duplicate_matches(candidate: dict, candidate_images: list[dict]) -> list[dict]:
    """Find issue groups matching image, location, category, or description signals."""
    grouped = {}
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT c.id, c.title, c.category, c.location, c.latitude, c.longitude,
                       c.description, c.status, c.created_by_user_id,
                       COALESCE(s.canonical_complaint_id, c.id) AS canonical_id,
                       e.id AS evidence_id, e.file_type, e.file_path,
                       e.sha256, e.perceptual_hash
                FROM complaints c
                LEFT JOIN complaint_supports s ON s.supporting_complaint_id = c.id
                LEFT JOIN evidence_files e
                  ON e.complaint_id = c.id AND e.file_type = 'image'
                ORDER BY c.created_at DESC
                """
            )
            rows = cursor.fetchall()
            for row in rows:
                canonical_id = row["canonical_id"]
                group = grouped.setdefault(canonical_id, {
                    "id": canonical_id,
                    "title": row["title"],
                    "category": row["category"],
                    "location": row["location"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "description": row["description"],
                    "status": row["status"],
                    "reporters": set(),
                    "images": [],
                })
                if row["id"] == canonical_id:
                    for field in ("title", "category", "location", "latitude", "longitude", "description", "status"):
                        group[field] = row[field]
                if row["created_by_user_id"]:
                    group["reporters"].add(row["created_by_user_id"])
                if not row["evidence_id"]:
                    continue

                stored_path = str(row["file_path"])
                image_path = _local_evidence_path(stored_path)
                sha256 = row["sha256"]
                perceptual_hash = row["perceptual_hash"]
                image_bytes = None
                if not sha256 or not perceptual_hash:
                    try:
                        if image_path:  # Backward compatibility with local evidence.
                            image_bytes = image_path.read_bytes()
                        elif stored_path.startswith("complaints/"):
                            image_bytes = download_evidence(stored_path)
                    except Exception:
                        logger.warning("Unable to read stored image evidence for duplicate checking.", exc_info=True)
                if image_bytes and (not sha256 or not perceptual_hash):
                    fingerprints = image_fingerprints(image_bytes)
                    if fingerprints:
                        sha256, perceptual_hash = fingerprints
                        cursor.execute(
                            "UPDATE evidence_files SET sha256 = %s, perceptual_hash = %s WHERE id = %s",
                            (sha256, perceptual_hash, row["evidence_id"]),
                        )
                group["images"].append({
                    "sha256": sha256,
                    "perceptual_hash": perceptual_hash,
                    "path": image_path,
                    "storage_path": stored_path if stored_path.startswith("complaints/") else None,
                })
        finally:
            cursor.close()

    matches = []
    for group in grouped.values():
        comparisons = []
        image_pairs = [
            (incoming, existing)
            for incoming in candidate_images
            for existing in group["images"]
        ]
        for incoming, existing in image_pairs:
            comparisons.append(compare_complaint(candidate | incoming, group | existing))
        if not image_pairs:
            comparisons.append(compare_complaint(candidate, group))
        best = max(comparisons, key=lambda result: result["score"])
        if not best["is_match"]:
            continue

        preview = None
        preview_item = next((image for image in group["images"] if image["path"] or image["storage_path"]), None)
        if preview_item:
            try:
                preview_data = (
                    preview_item["path"].read_bytes()
                    if preview_item["path"]
                    else download_evidence(preview_item["storage_path"])
                )
                preview = _image_preview_data(preview_data)
            except Exception:
                logger.warning("Unable to load matched evidence preview.", exc_info=True)
        matches.append({
            "id": group["id"],
            "title": group["title"],
            "category": group["category"],
            "location": group["location"],
            "status": group["status"],
            "report_count": len(group["reporters"]),
            "image_preview": preview,
            "score": best["score"],
            "reasons": best["reasons"],
        })
    return sorted(matches, key=lambda item: item["score"], reverse=True)[:5]


def _validate_duplicate_choice(matches: list[dict], support_existing_id: str | None, confirm_new: bool) -> str | None:
    """Require the citizen's explicit choice whenever the server finds a possible match."""
    if support_existing_id:
        if not any(match["id"] == support_existing_id for match in matches):
            raise HTTPException(
                status_code=409,
                detail="That complaint no longer matches this report. Please run the duplicate check again.",
            )
        return support_existing_id
    if matches and not confirm_new:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_confirmation_required",
                "message": "A similar complaint already exists! Review the matches before submitting.",
                "matches": matches,
            },
        )
    return None


@router.post("/complaints/check-duplicates")
async def check_complaint_duplicates(request: Request, user: dict = Depends(get_current_user)):
    if user["role"] != "citizen":
        raise HTTPException(status_code=403, detail="Only citizens can check complaint duplicates.")
    payload, uploads = await _parse_complaint_request(request)
    try:
        latitude = float(payload["latitude"]) if payload.get("latitude") not in (None, "") else None
        longitude = float(payload["longitude"]) if payload.get("longitude") not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Latitude and longitude must be valid numbers.") from exc
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="Provide both latitude and longitude, or leave both blank.")

    image_uploads = [item for item in uploads if (item.content_type or "").startswith("image/")]
    if len(image_uploads) > MAX_IMAGE_COUNT:
        raise HTTPException(status_code=400, detail=f"Upload no more than {MAX_IMAGE_COUNT} images.")
    fingerprints = []
    for image_upload in image_uploads:
        data = await image_upload.read()
        if len(data) > ALLOWED_EVIDENCE["image"]["max_size"]:
            raise HTTPException(status_code=413, detail="An image exceeds the 10 MB limit.")
        fingerprint = image_fingerprints(data)
        if fingerprint:
            fingerprints.append({"sha256": fingerprint[0], "perceptual_hash": fingerprint[1]})

    candidate = {
        "title": str(payload.get("title") or "").strip(),
        "category": str(payload.get("category") or "").strip(),
        "location": str(payload.get("location") or payload.get("location_text") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "latitude": latitude,
        "longitude": longitude,
    }
    matches = await run_in_threadpool(_find_duplicate_matches, candidate, fingerprints)
    return {"matches": matches}


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
            row = dict(row) if row is not None else None
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

    return _evidence_response(complaint["video_path"], complaint.get("video_name") or "evidence-video")


def _evidence_response(stored_path: str, filename: str, mime_type: str | None = None):
    """Serve private cloud evidence after the complaint access check has passed."""
    safe_filename = Path(filename).name
    media_type = mime_type or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
    resolved_legacy_path = _local_evidence_path(stored_path)
    if resolved_legacy_path and resolved_legacy_path.is_file():
        return FileResponse(
            resolved_legacy_path,
            media_type=media_type,
            headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
        )
    if not stored_path.startswith("complaints/"):
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.")
    try:
        content = download_evidence(stored_path)
    except Exception as exc:
        logger.exception("Unable to retrieve evidence from Supabase Storage.")
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.") from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
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

    return _evidence_response(evidence["file_path"], evidence["original_name"], evidence["mime_type"])


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
                await _save_uploaded_evidence(file_obj, user["id"], complaint_id)
            )

        candidate = {
            "title": title,
            "category": category,
            "location": location,
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
        }
        fingerprints = [
            {"sha256": item["sha256"], "perceptual_hash": item["perceptual_hash"]}
            for item in saved_evidence
            if item["file_type"] == "image" and item.get("sha256")
        ]
        matches = await run_in_threadpool(_find_duplicate_matches, candidate, fingerprints)
        canonical_complaint_id = _validate_duplicate_choice(
            matches,
            support_existing_id,
            payload.get("confirm_new_complaint") == "true",
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
        # Evidence is durable in Storage; this local copy is only for model inference.
        _cleanup_uploaded_evidence(saved_evidence, delete_remote=False)
        routed_department = None
        if not support_existing_id and analysis_result.get("analysis_status") == "completed":
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
                            file_size, file_path, uploaded_by, created_at, sha256,
                            perceptual_hash
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                            evidence_item.get("sha256"),
                            evidence_item.get("perceptual_hash"),
                        ),
                    )
                if canonical_complaint_id:
                    cursor.execute(
                        """
                        INSERT INTO complaint_supports (
                            supporting_complaint_id, canonical_complaint_id,
                            supported_by_user_id, created_at
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (complaint_id, canonical_complaint_id, user["id"], now),
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
        _cleanup_uploaded_evidence(saved_evidence, delete_remote=True)
        raise
    except Exception as exc:
        _cleanup_uploaded_evidence(saved_evidence, delete_remote=True)
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
    if canonical_complaint_id:
        with get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT created_by_user_id) AS report_count
                    FROM complaints c
                    LEFT JOIN complaint_supports s ON s.supporting_complaint_id = c.id
                    WHERE COALESCE(s.canonical_complaint_id, c.id) = %s
                    """,
                    (canonical_complaint_id,),
                )
                report_count = cursor.fetchone()["report_count"]
            finally:
                cursor.close()
        complaint["supported_complaint_id"] = canonical_complaint_id
        complaint["status"] = "Supported"
        complaint["support_report_count"] = report_count
    return complaint


@router.get("/complaints/{complaint_id}/details")
async def complaint_details(complaint_id: str, user: dict = Depends(get_current_user)):
    return await get_complaint(complaint_id, user)
