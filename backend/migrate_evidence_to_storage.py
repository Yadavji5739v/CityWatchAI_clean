"""Copy legacy local complaint evidence to private Supabase Storage.

Run from backend after setting DATABASE_URL, SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY. The default is a dry run; add --apply to copy and
update database paths. Local source files are never deleted.
"""

import argparse
import hashlib
import logging
import mimetypes
from pathlib import Path

from database import BASE_DIR, get_connection
from services.duplicate_detection import image_fingerprints
from services.supabase_client import upload_evidence

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("evidence-migration")
UPLOADS_DIR = (BASE_DIR / "uploads").resolve()


def local_source(stored_path: str) -> Path | None:
    path = Path(stored_path)
    candidate = path if path.is_absolute() else BASE_DIR / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(UPLOADS_DIR)
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Upload objects and update paths in PostgreSQL")
    args = parser.parse_args()
    migrated = 0
    skipped = 0
    failed = 0

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, complaint_id, original_name, file_type, mime_type, file_path, sha256, perceptual_hash "
                "FROM evidence_files ORDER BY created_at"
            )
            evidence_rows = cursor.fetchall()
            cursor.execute("SELECT id, video_name, video_path FROM complaints WHERE video_path IS NOT NULL")
            video_rows = cursor.fetchall()
        finally:
            cursor.close()

    for item in evidence_rows:
        source = local_source(item["file_path"])
        if not source:
            skipped += 1
            continue
        content = source.read_bytes()
        suffix = source.suffix.lower()
        storage_path = f"complaints/{item['complaint_id']}/{item['id']}{suffix}"
        if args.apply:
            try:
                upload_evidence(storage_path, content, item["mime_type"], upsert=True)
                fingerprints = image_fingerprints(content) if item["file_type"] == "image" else None
                with get_connection() as connection:
                    cursor = connection.cursor()
                    try:
                        cursor.execute(
                            "UPDATE evidence_files SET file_path = %s, sha256 = COALESCE(sha256, %s), "
                            "perceptual_hash = COALESCE(perceptual_hash, %s) WHERE id = %s",
                            (storage_path, fingerprints[0] if fingerprints else None,
                             fingerprints[1] if fingerprints else None, item["id"]),
                        )
                        if item["file_type"] == "video":
                            cursor.execute(
                                "UPDATE complaints SET video_path = %s WHERE id = %s AND video_path = %s",
                                (storage_path, item["complaint_id"], item["file_path"]),
                            )
                    finally:
                        cursor.close()
                migrated += 1
            except Exception:
                failed += 1
                logger.exception("Failed to migrate evidence id %s", item["id"])
        else:
            logger.info("Would migrate %s (%s bytes) -> %s", item["id"], len(content), storage_path)
            migrated += 1

    # Older complaints may have a video_path without a matching evidence_files row.
    evidence_video_paths = {item["file_path"] for item in evidence_rows if item["file_type"] == "video"}
    for item in video_rows:
        if item["video_path"] in evidence_video_paths or not local_source(item["video_path"]):
            continue
        source = local_source(item["video_path"])
        if not source:
            continue
        content = source.read_bytes()
        suffix = source.suffix.lower()
        fingerprint = hashlib.sha256(content).hexdigest()[:20]
        storage_path = f"complaints/{item['id']}/legacy-video-{fingerprint}{suffix}"
        if args.apply:
            try:
                upload_evidence(
                    storage_path, content,
                    mimetypes.guess_type(item["video_name"] or source.name)[0] or "application/octet-stream",
                    upsert=True,
                )
                with get_connection() as connection:
                    cursor = connection.cursor()
                    try:
                        cursor.execute("UPDATE complaints SET video_path = %s WHERE id = %s", (storage_path, item["id"]))
                    finally:
                        cursor.close()
                migrated += 1
            except Exception:
                failed += 1
                logger.exception("Failed to migrate legacy video for complaint %s", item["id"])
        else:
            logger.info("Would migrate legacy video for %s (%s bytes) -> %s", item["id"], len(content), storage_path)
            migrated += 1

    logger.info("%s: %s copied/planned, %s already cloud/missing, %s failed", "apply" if args.apply else "dry run", migrated, skipped, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
