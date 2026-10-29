"""AI analysis routes."""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from services.ai_service import analyze_video
from services.auth_helpers import get_authenticated_client, get_user_id_from_client, get_user_profile
from services.priority_service import calculate_priority_score

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/complaints/{complaint_id}/analyze")
async def trigger_analysis(
    complaint_id: str,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """Trigger AI analysis on a complaint's video evidence."""
    client = get_authenticated_client(authorization)
    user_id = get_user_id_from_client(client)
    profile = get_user_profile(client, user_id)
    role = profile.get("role", "citizen")

    if role not in {"admin", "officer"}:
        raise HTTPException(status_code=403, detail="Only admins or officers can trigger analysis")

    # Get complaint
    complaint = (
        client.table("complaints")
        .select("id, category, latitude, longitude")
        .eq("id", complaint_id)
        .single()
        .execute()
    )
    if not complaint.data:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Get video evidence
    evidence = (
        client.table("evidence_files")
        .select("storage_path")
        .eq("complaint_id", complaint_id)
        .eq("file_type", "video")
        .limit(1)
        .execute()
    )

    analysis_result = None

    if evidence.data:
        storage_path = evidence.data[0]["storage_path"]

        # Download video to temp file
        try:
            video_bytes = client.storage.from_("evidence").download(storage_path)

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name

            # Run AI analysis
            analysis_result = analyze_video(tmp_path)

            # Clean up temp file
            os.unlink(tmp_path)
        except Exception as e:
            analysis_result = {
                "analysis_status": "failed",
                "error_message": f"Could not process video: {str(e)}",
                "processing_time_ms": 0,
            }
    else:
        # No video — run priority assessment only
        priority_result = calculate_priority_score(
            category=complaint.data.get("category", "other"),
            has_video=False,
            has_location=bool(complaint.data.get("latitude")),
        )
        analysis_result = {
            "analysis_status": "completed",
            "model_name": "priority_only",
            "detected_classes": [],
            "confidence_data": [],
            "frame_timestamps": [],
            "summary": "No video evidence available. Priority assessed based on category and location only.",
            "suggested_priority": priority_result["priority"],
            "priority_details": priority_result,
            "processing_time_ms": 0,
        }

    # Update complaint status
    client.table("complaints").update({"status": "ai_analysis"}).eq("id", complaint_id).execute()

    # Save analysis to DB
    db_record = {
        "complaint_id": complaint_id,
        "model_name": analysis_result.get("model_name", "yolov8n"),
        "model_version": analysis_result.get("model_version"),
        "detected_classes": analysis_result.get("detected_classes", []),
        "confidence_data": analysis_result.get("confidence_data", []),
        "frame_timestamps": analysis_result.get("frame_timestamps", []),
        "suggested_priority": analysis_result.get("suggested_priority"),
        "summary": analysis_result.get("summary"),
        "analysis_status": analysis_result.get("analysis_status", "completed"),
        "error_message": analysis_result.get("error_message"),
        "processing_time_ms": analysis_result.get("processing_time_ms"),
    }

    saved = client.table("ai_analyses").insert(db_record).execute()

    # Update priority if suggested
    if analysis_result.get("suggested_priority"):
        client.table("complaints").update({
            "priority": analysis_result["suggested_priority"],
            "status": "pending_review",
        }).eq("id", complaint_id).execute()

    # Log
    client.table("complaint_history").insert({
        "complaint_id": complaint_id,
        "actor_id": user_id,
        "action": "ai_analysis_triggered",
        "new_status": "pending_review",
    }).execute()

    return {
        "message": "Analysis complete",
        "analysis": analysis_result,
        "record_id": saved.data[0]["id"] if saved.data else None,
    }


@router.get("/complaints/{complaint_id}/analysis")
async def get_analysis(
    complaint_id: str,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """Get AI analysis results for a complaint."""
    client = get_authenticated_client(authorization)
    get_user_id_from_client(client)  # auth check

    response = (
        client.table("ai_analyses")
        .select("*")
        .eq("complaint_id", complaint_id)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []
