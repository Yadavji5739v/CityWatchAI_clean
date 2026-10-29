"""
AI video analysis service using OpenCV + YOLO.

Limitations of the pretrained YOLOv8 model (COCO dataset):
- CAN detect: person, car, truck, bus, motorcycle, bicycle, traffic light, stop sign, fire hydrant
- CANNOT reliably detect: potholes, garbage piles, waterlogging, broken streetlights, road cracks
- For civic-specific detection, a fine-tuned model trained on relevant datasets is recommended.

This service extracts frames from uploaded videos, runs YOLO object detection,
and aggregates results. It is meant to *assist* human reviewers, not to
independently determine complaint validity.
"""

import json
import logging
import os
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Frame extraction interval in seconds (configurable)
FRAME_INTERVAL_SECONDS = float(os.getenv("AI_FRAME_INTERVAL", "2.0"))
MAX_FRAMES = int(os.getenv("AI_MAX_FRAMES", "15"))
CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.35"))
MODEL_NAME = os.getenv("AI_MODEL_NAME", "yolov8n")

# COCO classes that are relevant to civic complaints
CIVIC_RELEVANT_CLASSES = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "traffic light", "fire hydrant", "stop sign",
    "dog", "cat",  # stray animals
}


def _load_model():
    """Lazy-load the YOLO model."""
    try:
        from ultralytics import YOLO
        model_path = f"{MODEL_NAME}.pt"
        model = YOLO(model_path)
        logger.info(f"Loaded YOLO model: {model_path}")
        return model
    except ImportError:
        logger.warning("ultralytics not installed. AI analysis will return mock results.")
        return None
    except Exception as e:
        logger.error(f"Failed to load YOLO model: {e}")
        return None


# Module-level model (lazy singleton)
_model = None


def get_model():
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def extract_frames(video_path: str, interval: float = FRAME_INTERVAL_SECONDS, max_frames: int = MAX_FRAMES) -> list[dict]:
    """
    Extract representative frames from a video at the given interval.
    Returns list of dicts: {"frame": numpy_array, "timestamp_sec": float, "frame_index": int}
    """
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV not installed. Returning empty frames.")
        return []

    frames = []
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # fallback

    frame_interval = int(fps * interval)
    frame_count = 0
    extracted = 0

    while cap.isOpened() and extracted < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            frames.append({
                "frame": frame,
                "timestamp_sec": round(timestamp, 2),
                "frame_index": frame_count,
            })
            extracted += 1

        frame_count += 1

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from {video_path}")
    return frames


def detect_objects(frames: list[dict], confidence_threshold: float = CONFIDENCE_THRESHOLD) -> list[dict]:
    """
    Run YOLO detection on extracted frames.
    Returns aggregated detection results.
    """
    model = get_model()
    all_detections = []

    if model is None:
        # Return mock/demo results when model is unavailable
        logger.info("Using mock AI detections (model not available)")
        return [{
            "class": "vehicle",
            "confidence": 0.72,
            "timestamp_sec": 1.0,
            "frame_index": 0,
            "bbox": [100, 100, 300, 300],
            "note": "Mock detection — YOLO model not loaded",
        }]

    for frame_data in frames:
        frame = frame_data["frame"]
        timestamp = frame_data["timestamp_sec"]
        frame_idx = frame_data["frame_index"]

        try:
            results = model(frame, verbose=False)

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < confidence_threshold:
                        continue

                    cls_id = int(box.cls[0])
                    cls_name = model.names.get(cls_id, f"class_{cls_id}")

                    # Only keep civic-relevant detections
                    if cls_name.lower() not in CIVIC_RELEVANT_CLASSES:
                        continue

                    bbox = box.xyxy[0].tolist()
                    all_detections.append({
                        "class": cls_name,
                        "confidence": round(conf, 3),
                        "timestamp_sec": timestamp,
                        "frame_index": frame_idx,
                        "bbox": [round(v, 1) for v in bbox],
                    })
        except Exception as e:
            logger.error(f"Detection failed on frame {frame_idx}: {e}")
            continue

    return all_detections


def aggregate_detections(detections: list[dict]) -> dict:
    """
    Aggregate raw detections into a summary.
    Returns dict with class counts, top detections, confidence stats.
    """
    if not detections:
        return {
            "total_detections": 0,
            "unique_classes": [],
            "class_counts": {},
            "avg_confidence": 0,
            "max_confidence": 0,
            "top_detections": [],
            "summary": "No relevant objects detected in the video frames.",
        }

    class_counts = {}
    confidences = []

    for d in detections:
        cls = d["class"]
        class_counts[cls] = class_counts.get(cls, 0) + 1
        confidences.append(d["confidence"])

    avg_conf = sum(confidences) / len(confidences)
    max_conf = max(confidences)

    # Top detections: highest confidence per class
    top = {}
    for d in detections:
        cls = d["class"]
        if cls not in top or d["confidence"] > top[cls]["confidence"]:
            top[cls] = d

    top_list = sorted(top.values(), key=lambda x: x["confidence"], reverse=True)

    # Generate human-readable summary
    class_summary = ", ".join(
        f"{count}× {cls}" for cls, count in
        sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    )

    summary = (
        f"Detected {len(detections)} relevant objects across frames: {class_summary}. "
        f"Average confidence: {avg_conf:.0%}. "
        f"Note: This pretrained model (COCO) may not detect specific civic issues like potholes or garbage. "
        f"Results should be reviewed by an authorized officer."
    )

    return {
        "total_detections": len(detections),
        "unique_classes": list(class_counts.keys()),
        "class_counts": class_counts,
        "avg_confidence": round(avg_conf, 3),
        "max_confidence": round(max_conf, 3),
        "top_detections": top_list[:10],
        "summary": summary,
    }


def analyze_video(video_path: str) -> dict:
    """
    Full analysis pipeline: extract frames → detect objects → aggregate.
    Returns complete analysis result.
    """
    start = time.time()

    frames = extract_frames(video_path)
    if not frames:
        return {
            "analysis_status": "failed",
            "error_message": "Could not extract frames from the video.",
            "processing_time_ms": int((time.time() - start) * 1000),
        }

    detections = detect_objects(frames)
    aggregated = aggregate_detections(detections)

    # Import priority service for suggested priority
    from services.priority_service import calculate_priority_score

    priority_result = calculate_priority_score(
        category="other",  # will be updated by caller
        ai_detections=detections,
        has_video=True,
        has_location=False,
    )

    processing_time = int((time.time() - start) * 1000)

    return {
        "analysis_status": "completed",
        "model_name": MODEL_NAME,
        "model_version": "pretrained-coco",
        "detected_classes": aggregated["unique_classes"],
        "confidence_data": detections,
        "frame_timestamps": [f["timestamp_sec"] for f in frames],
        "summary": aggregated["summary"],
        "aggregated": aggregated,
        "suggested_priority": priority_result["priority"],
        "priority_details": priority_result,
        "processing_time_ms": processing_time,
        "limitations": (
            "This analysis uses a pretrained YOLOv8 model trained on the COCO dataset. "
            "It can detect common objects (vehicles, people, traffic lights) but cannot "
            "reliably identify potholes, garbage accumulation, waterlogging, or broken "
            "streetlights. For accurate civic issue detection, a fine-tuned model trained "
            "on relevant datasets is recommended."
        ),
    }
