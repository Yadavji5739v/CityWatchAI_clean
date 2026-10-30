"""Authenticated evidence upload and listing backed by Supabase Storage."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from database import get_connection
from services.local_auth import get_current_user
from services.supabase_client import delete_evidence, upload_evidence

router = APIRouter(prefix="/api", tags=["evidence"])
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo",
    "video/x-matroska", "video/ogg", "image/jpeg", "image/png", "image/webp", "image/gif",
}
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"},
    "image/gif": {".gif"}, "video/mp4": {".mp4"}, "video/webm": {".webm"},
    "video/quicktime": {".mov"}, "video/x-msvideo": {".avi"},
    "video/x-matroska": {".mkv"}, "video/ogg": {".ogv", ".ogg"},
}


@router.post("/complaints/{complaint_id}/evidence", status_code=status.HTTP_201_CREATED)
async def upload_evidence_route(
    complaint_id: str,
    file: UploadFile = File(...),
    file_type: str = Form("video"),
    user: dict = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES or content_type.split("/", 1)[0] != file_type:
        raise HTTPException(status_code=400, detail="Choose a supported image or video file.")
    original_name = Path(file.filename or "evidence").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS.get(content_type, set()):
        raise HTTPException(status_code=400, detail="The filename extension does not match the evidence type.")
    max_size = MAX_IMAGE_SIZE if file_type == "image" else MAX_FILE_SIZE
    content = await file.read(max_size + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Empty files cannot be uploaded.")
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"Evidence exceeds the {max_size // (1024 * 1024)} MB upload limit.")

    evidence_id = str(uuid.uuid4())
    storage_path = f"complaints/{complaint_id}/{evidence_id}{extension}"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    uploaded = False
    try:
        with get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute("SELECT created_by_user_id FROM complaints WHERE id = %s", (complaint_id,))
                complaint = cursor.fetchone()
                if not complaint:
                    raise HTTPException(status_code=404, detail="Complaint not found.")
                if user["role"] == "citizen" and complaint["created_by_user_id"] != user["id"]:
                    raise HTTPException(status_code=403, detail="You can only add evidence to your own complaint.")
                upload_evidence(storage_path, content, content_type)
                uploaded = True
                cursor.execute(
                    """INSERT INTO evidence_files
                       (id, complaint_id, original_name, file_type, mime_type, file_size,
                        file_path, uploaded_by, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (evidence_id, complaint_id, original_name, file_type, content_type,
                     len(content), storage_path, user["id"], now),
                )
                cursor.execute(
                    """INSERT INTO complaint_history
                       (complaint_id, actor_id, action, created_at)
                       VALUES (%s, %s, %s, %s)""",
                    (complaint_id, user["id"], f"{file_type}_evidence_uploaded", now),
                )
            finally:
                cursor.close()
    except HTTPException:
        if uploaded:
            try:
                delete_evidence(storage_path)
            except Exception:
                logger.exception("Could not roll back an evidence object after a failed database write.")
        raise
    except Exception as exc:
        if uploaded:
            try:
                delete_evidence(storage_path)
            except Exception:
                logger.exception("Could not roll back an evidence object after a failed database write.")
        logger.exception("Evidence upload failed.")
        raise HTTPException(status_code=503, detail="Evidence could not be saved. Please try again.") from exc

    return {
        "message": "Evidence uploaded successfully",
        "file_path": storage_path,
        "file_size": len(content),
        "record": {
            "id": evidence_id, "complaint_id": complaint_id, "original_name": original_name,
            "file_type": file_type, "mime_type": content_type, "file_size": len(content),
            "url": f"/api/complaints/{complaint_id}/evidence/{evidence_id}",
        },
    }


@router.get("/complaints/{complaint_id}/evidence")
async def list_evidence_route(complaint_id: str, user: dict = Depends(get_current_user)):
    from routes.complaints import get_complaint

    await get_complaint(complaint_id, user)
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, original_name, file_type, mime_type, file_size, created_at "
                "FROM evidence_files WHERE complaint_id = %s ORDER BY created_at",
                (complaint_id,),
            )
            files = cursor.fetchall()
        finally:
            cursor.close()
    return [
        {**item, "url": f"/api/complaints/{complaint_id}/evidence/{item['id']}"}
        for item in files
    ]
