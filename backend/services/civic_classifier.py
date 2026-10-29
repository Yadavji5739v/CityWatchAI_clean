"""Inference adapter for the bundled five-class civic issue model."""

import logging
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from database import BASE_DIR

logger = logging.getLogger(__name__)

_configured_model_path = Path(os.getenv(
    "CITYWATCH_ROAD_MODEL_PATH",
    "models/road_damage_5class_model.keras",
))
MODEL_PATH = (
    _configured_model_path
    if _configured_model_path.is_absolute()
    else BASE_DIR / _configured_model_path
)
CLASS_NAMES = ("crack", "garbage", "manhole", "poor_drainage", "pothole")
SUPPORTED_REPORT_CATEGORIES = {
    "pothole",
    "road_damage",
    "garbage",
    "garbage_waste",
    "drainage",
    "poor_drainage",
    "water_logging",
}
CONFIDENCE_THRESHOLD = float(os.getenv("CITYWATCH_AI_CONFIDENCE_THRESHOLD", "0.40"))
INPUT_SIZE = (224, 224)
MAX_VIDEO_FRAMES = 12
VIDEO_FRAME_INTERVAL_SECONDS = 2

_model = None
_model_loaded = False


def _load_model():
    if not MODEL_PATH.is_file():
        logger.warning("Road damage model is missing: %s", MODEL_PATH)
        return None

    try:
        import tensorflow as tf
    except ImportError:
        logger.warning("TensorFlow is not installed; civic issue analysis is unavailable.")
        return None

    try:
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    except Exception:
        logger.exception("Unable to load the road damage model at %s.", MODEL_PATH)
        return None

    output_shape = model.output_shape
    if not output_shape or output_shape[-1] != len(CLASS_NAMES):
        logger.error(
            "Road damage model output has shape %s; expected %s classes.",
            output_shape,
            len(CLASS_NAMES),
        )
        return None
    return model


def _get_model():
    global _model, _model_loaded
    if not _model_loaded:
        _model = _load_model()
        _model_loaded = True
    return _model


def _image_tensor(image: Image.Image) -> np.ndarray:
    resized = image.convert("RGB").resize(INPUT_SIZE)
    tensor = np.asarray(resized, dtype=np.float32)
    return (tensor / 127.5 - 1.0)[np.newaxis, ...]


def _video_frames(path: Path) -> list[Image.Image]:
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV is unavailable; video classification cannot run.")
        return []

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        return []

    fps = capture.get(cv2.CAP_PROP_FPS)
    interval = max(int(fps * VIDEO_FRAME_INTERVAL_SECONDS), 1) if fps > 0 else 60
    frames = []
    frame_index = 0
    try:
        while len(frames) < MAX_VIDEO_FRAMES:
            success, frame = capture.read()
            if not success:
                break
            if frame_index % interval == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(rgb))
            frame_index += 1
    finally:
        capture.release()
    return frames


def _evidence_frames(path: Path, file_type: str) -> list[Image.Image]:
    if file_type == "video":
        return _video_frames(path)
    try:
        with Image.open(path) as image:
            return [image.copy()]
    except (OSError, UnidentifiedImageError):
        logger.exception("Unable to decode image evidence %s.", path)
        return []


def classify_evidence(evidence: list[dict], reported_category: str) -> dict:
    """Classify supported civic reports using real model outputs only."""
    started = time.perf_counter()
    normalized_category = "_".join(
        reported_category.lower().replace("/", " ").split()
    )
    if normalized_category not in SUPPORTED_REPORT_CATEGORIES:
        return {
            "analysis_status": "unsupported_category",
            "model_name": "road_damage_5class_model",
            "predicted_category": None,
            "confidence": None,
            "predictions": [],
            "summary": "The bundled model does not support this category; human review is required.",
            "processing_time_ms": 0,
        }

    frames = []
    try:
        for item in evidence:
            frames.extend(_evidence_frames(Path(item["path"]), item["file_type"]))
    except Exception:
        logger.exception("Unable to extract frames from complaint evidence.")
        return {
            "analysis_status": "failed",
            "model_name": "road_damage_5class_model",
            "predicted_category": None,
            "confidence": None,
            "predictions": [],
            "summary": "Evidence processing failed; complaint left for human review.",
            "error_message": "Evidence processing failed.",
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        }
    if not frames:
        return {
            "analysis_status": "failed",
            "model_name": "road_damage_5class_model",
            "predicted_category": None,
            "confidence": None,
            "predictions": [],
            "summary": "No readable image frames could be extracted from the evidence.",
            "error_message": "Evidence could not be decoded.",
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        }

    model = _get_model()
    if model is None:
        return {
            "analysis_status": "unavailable",
            "model_name": "road_damage_5class_model",
            "predicted_category": None,
            "confidence": None,
            "predictions": [],
            "summary": "The trained road damage model is unavailable; complaint left for human review.",
            "error_message": "Model file or TensorFlow runtime is unavailable.",
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        }

    try:
        frame_predictions = [
            np.asarray(model.predict(_image_tensor(frame), verbose=0)[0], dtype=np.float32)
            for frame in frames
        ]
    except Exception:
        logger.exception("Road damage model inference failed.")
        return {
            "analysis_status": "failed",
            "model_name": "road_damage_5class_model",
            "predicted_category": None,
            "confidence": None,
            "predictions": [],
            "summary": "The trained model could not analyze this evidence; complaint left for human review.",
            "error_message": "Model inference failed.",
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        }

    if any(prediction.shape != (len(CLASS_NAMES),) for prediction in frame_predictions):
        logger.error("Road damage model returned an unexpected prediction shape.")
        return {
            "analysis_status": "failed",
            "model_name": "road_damage_5class_model",
            "predicted_category": None,
            "confidence": None,
            "predictions": [],
            "summary": "The trained model returned an unsupported result; complaint left for human review.",
            "error_message": "Model output shape did not match its documented class mapping.",
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        }

    scores = np.mean(frame_predictions, axis=0)
    best_index = int(np.argmax(scores))
    confidence = float(scores[best_index])
    predicted_category = CLASS_NAMES[best_index]
    predictions = [
        {"class": CLASS_NAMES[index], "confidence": round(float(score), 4)}
        for index, score in enumerate(scores)
    ]
    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "analysis_status": "review_required",
            "model_name": "road_damage_5class_model",
            "model_version": "five-class",
            "predicted_category": None,
            "confidence": round(confidence, 4),
            "predictions": predictions,
            "summary": "Model confidence is below the automatic routing threshold; complaint left for human review.",
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        }

    return {
        "analysis_status": "completed",
        "model_name": "road_damage_5class_model",
        "model_version": "five-class",
        "predicted_category": predicted_category,
        "confidence": round(confidence, 4),
        "predictions": predictions,
        "summary": (
            f"Model classified the evidence as {predicted_category} "
            f"with {confidence:.0%} confidence. Reviewer verification is still required."
        ),
        "processing_time_ms": int((time.perf_counter() - started) * 1000),
    }
