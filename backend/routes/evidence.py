"""Evidence file upload routes."""

from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status

from services.auth_helpers import get_authenticated_client, get_user_id_from_client, get_user_profile

router = APIRouter(prefix="/api", tags=["evidence"])

# Allowed video MIME types
ALLOWED_VIDEO_TYPES = {
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo",
    "video/x-matroska", "video/ogg",
}
ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/complaints/{complaint_id}/evidence")
async def upload_evidence(
    complaint_id: str,
    file: UploadFile = File(...),
    file_type: str = Form("video"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """Upload video or image evidence for a complaint."""
    client = get_authenticated_client(authorization)
    user_id = get_user_id_from_client(client)

    # Verify complaint exists and user has access
    complaint = (
        client.table("complaints")
        .select("citizen_id")
        .eq("id", complaint_id)
        .single()
        .execute()
    )
    if not complaint.data:
        raise HTTPException(status_code=404, detail="Complaint not found")

    profile = get_user_profile(client, user_id)
    role = profile.get("role", "citizen")
    if complaint.data["citizen_id"] != user_id and role not in {"admin", "officer"}:
        raise HTTPException(status_code=403, detail="Not authorized to upload evidence for this complaint")

    # Validate file type
    content_type = file.content_type or ""
    if file_type == "video" and content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video type: {content_type}. Allowed: {', '.join(ALLOWED_VIDEO_TYPES)}",
        )
    if file_type == "image" and content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum: {MAX_FILE_SIZE // (1024*1024)} MB")

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file not allowed")

    # Upload to Supabase Storage
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    storage_path = f"{complaint_id}/{user_id}_{filename}"

    try:
        storage_response = client.storage.from_("evidence").upload(
            storage_path,
            file_bytes,
            file_options={"content-type": content_type or "application/octet-stream"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    # Create evidence record
    evidence_record = client.table("evidence_files").insert({
        "complaint_id": complaint_id,
        "storage_path": storage_path,
        "file_type": file_type,
        "file_size": len(file_bytes),
        "uploaded_by": user_id,
    }).execute()

    # Log in history
    client.table("complaint_history").insert({
        "complaint_id": complaint_id,
        "actor_id": user_id,
        "action": f"{file_type}_evidence_uploaded",
    }).execute()

    return {
        "message": "Evidence uploaded successfully",
        "file_path": storage_path,
        "file_size": len(file_bytes),
        "record": evidence_record.data[0] if evidence_record.data else None,
    }


@router.get("/complaints/{complaint_id}/evidence")
async def list_evidence(
    complaint_id: str,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """List all evidence files for a complaint."""
    client = get_authenticated_client(authorization)
    user_id = get_user_id_from_client(client)

    # Access check done by RLS
    response = (
        client.table("evidence_files")
        .select("*")
        .eq("complaint_id", complaint_id)
        .order("created_at", desc=False)
        .execute()
    )

    return response.data or []
