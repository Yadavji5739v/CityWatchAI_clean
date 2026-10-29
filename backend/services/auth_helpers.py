from typing import Any, Optional

from fastapi import Header, HTTPException, status
from supabase import Client, create_client

from services.supabase_client import SUPABASE_ANON_KEY, SUPABASE_READY, SUPABASE_URL


def get_authenticated_client(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> Client:
    if not SUPABASE_READY or not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured. Add a valid SUPABASE_URL and SUPABASE_ANON_KEY to backend/.env.",
        )

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    token = authorization.replace("Bearer", "", 1).strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")

    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options={"global": {"headers": {"Authorization": f"Bearer {token}"}}},
    )


def get_user_id_from_client(client: Client) -> str:
    try:
        user_response = client.auth.get_user()
        if not user_response or not getattr(user_response, "user", None):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")
        return str(user_response.user.id)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_user_profile(client: Client, user_id: str) -> dict[str, Any]:
    try:
        response = client.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
        if response and response.data:
            return response.data
    except Exception:
        pass

    return {"role": "citizen", "full_name": "Citizen User", "department_id": None, "id": user_id}
