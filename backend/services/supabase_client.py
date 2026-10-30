import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "evidence").strip()


def _build_client(api_key: str | None = None) -> Client | None:
    if not SUPABASE_URL or not api_key:
        return None

    try:
        return create_client(SUPABASE_URL, api_key)
    except Exception:
        return None


supabase: Client | None = _build_client(SUPABASE_ANON_KEY)
SUPABASE_READY = supabase is not None


def admin_supabase():
    """Server-side only; keep the service-role key in the backend environment."""
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for admin operations.")

    client = _build_client(SUPABASE_SERVICE_ROLE_KEY)
    if client is None:
        raise ValueError("Supabase admin client could not be created. Check your keys.")
    return client


@lru_cache(maxsize=1)
def storage_client():
    """Return the server-side client used for private evidence objects."""
    return admin_supabase()


def upload_evidence(storage_path: str, content: bytes, content_type: str, *, upsert: bool = False) -> None:
    storage_client().storage.from_(SUPABASE_STORAGE_BUCKET).upload(
        storage_path,
        content,
        file_options={"content-type": content_type, "upsert": "true" if upsert else "false"},
    )


def download_evidence(storage_path: str) -> bytes:
    return storage_client().storage.from_(SUPABASE_STORAGE_BUCKET).download(storage_path)


def delete_evidence(storage_path: str) -> None:
    storage_client().storage.from_(SUPABASE_STORAGE_BUCKET).remove([storage_path])
