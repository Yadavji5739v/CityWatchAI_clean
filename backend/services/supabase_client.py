import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


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
