"""PostgreSQL-backed login and signed API sessions."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from typing import Optional

import psycopg2
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from database import BASE_DIR, get_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])
PASSWORD_ROUNDS = 260_000
TOKEN_LIFETIME_SECONDS = 8 * 60 * 60

DEMO_DEPARTMENTS = (
    ("roads", "Roads & Public Works"),
    ("sanitation", "Sanitation Department"),
    ("drainage", "Drainage Department"),
    ("electrical", "Electrical Maintenance Department"),
    ("water", "Water Supply Department"),
    ("traffic", "Traffic Department"),
)


class LoginRequest(BaseModel):
    id: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    mobile: str = Field(min_length=7, max_length=32)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Enter your full name.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[+0-9()\-\s]{7,32}", value) or sum(char.isdigit() for char in value) < 7:
            raise ValueError("Enter a valid mobile number.")
        return value


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _signing_secret() -> bytes:
    configured_secret = os.getenv("SECRET_KEY") or os.getenv("CITYWATCH_JWT_SECRET")
    if configured_secret:
        secret = configured_secret.encode("utf-8")
        if len(secret) < 32:
            raise RuntimeError("SECRET_KEY / CITYWATCH_JWT_SECRET must contain at least 32 characters.")
        return secret

    secret_path = BASE_DIR / "data" / ".jwt_secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(secret_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return secret_path.read_bytes()

    secret = secrets.token_bytes(48)
    with os.fdopen(descriptor, "wb") as secret_file:
        secret_file.write(secret)
    return secret


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS)
    return f"pbkdf2_sha256${PASSWORD_ROUNDS}${_urlsafe_encode(salt)}${_urlsafe_encode(digest)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, rounds_text, salt_text, digest_text = encoded_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        expected_digest = _urlsafe_decode(digest_text)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _urlsafe_decode(salt_text),
            rounds,
        )
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False


def _create_token(user: dict) -> str:
    issued_at = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "iat": issued_at,
        "exp": issued_at + TOKEN_LIFETIME_SECONDS,
    }
    encoded_header = _urlsafe_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _urlsafe_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(_signing_secret(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_urlsafe_encode(signature)}"


def _read_token(token: str) -> dict:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected_signature = hmac.new(_signing_secret(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_signature, _urlsafe_decode(encoded_signature)):
            raise ValueError("Invalid token signature")
        header = json.loads(_urlsafe_decode(encoded_header))
        payload = json.loads(_urlsafe_decode(encoded_payload))
        if header.get("alg") != "HS256" or int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Expired or unsupported token")
        if not payload.get("sub") or not payload.get("role"):
            raise ValueError("Incomplete token")
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _department_id(slug: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"citywatch-department:{slug}"))


def init_demo_accounts() -> None:
    """Create sample identities and departments once without overwriting real records."""
    if os.getenv("ENVIRONMENT", "development").lower() == "production" and os.getenv("CITYWATCH_SEED_DEMO_ACCOUNTS", "false").lower() != "true":
        return
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.executemany(
                "INSERT INTO departments (id, name, is_active) VALUES (%s, %s, 1) ON CONFLICT (id) DO NOTHING",
                [(_department_id(slug), name) for slug, name in DEMO_DEPARTMENTS],
            )

            demo_users = [
                ("CW-CIT-1001", "Demo Citizen", "citizen", None, "Citizen@123"),
                ("CW-ADM-3001", "Demo Administrator", "admin", None, "Admin@123"),
                ("CW-OFF-2001", "Demo Roads Officer", "officer", "roads", "Officer@123"),
                ("CW-OFF-2002", "Demo Sanitation Officer", "officer", "sanitation", "Officer@123"),
                ("CW-OFF-2003", "Demo Drainage Officer", "officer", "drainage", "Officer@123"),
                ("CW-OFF-2004", "Demo Electrical Officer", "officer", "electrical", "Officer@123"),
                ("CW-OFF-2005", "Demo Water Officer", "officer", "water", "Officer@123"),
                ("CW-OFF-2006", "Demo Traffic Officer", "officer", "traffic", "Officer@123"),
            ]
            cursor.execute("SELECT id FROM users")
            existing_user_ids = {row[0] for row in cursor.fetchall()}
            department_ids = {slug: _department_id(slug) for slug, _ in DEMO_DEPARTMENTS}
            missing_users = [
                (
                    account_id,
                    full_name,
                    role,
                    department_ids.get(department_slug),
                    hash_password(password),
                )
                for account_id, full_name, role, department_slug, password in demo_users
                if account_id not in existing_user_ids
            ]
            if missing_users:
                cursor.executemany(
                    """
                    INSERT INTO users
                        (id, full_name, role, department_id, password_hash, is_active, is_demo)
                    VALUES (%s, %s, %s, %s, %s, 1, 1)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    missing_users,
                )
        finally:
            cursor.close()


def get_current_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = _read_token(authorization[7:].strip())
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, full_name, role, department_id, is_active, is_demo
                FROM users WHERE id = %s
                """,
                (claims["sub"],),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()

    if not user or not user["is_active"] or user["role"] != claims["role"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive or the session is no longer valid.",
        )
    return user


@router.post("/login")
def login(request: LoginRequest):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, full_name, role, department_id, password_hash, is_active, is_demo
                FROM users
                WHERE id = %s OR LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (request.id.strip(), request.id.strip()),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()

    if not user or not user["is_active"] or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Account ID or password is incorrect.")

    public_user = {
        "id": user["id"],
        "name": user["full_name"],
        "role": user["role"],
        "department_id": user["department_id"],
    }
    return {"access_token": _create_token(public_user), "token_type": "bearer", "user": public_user}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: SignupRequest):
    account_id = f"CW-CIT-{secrets.token_hex(4).upper()}"

    try:
        with get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT id FROM users WHERE LOWER(email) = LOWER(%s)",
                    (request.email,),
                )
                if cursor.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An account with this email already exists.",
                    )

                cursor.execute(
                    """
                    INSERT INTO users (
                        id, full_name, email, phone, role, password_hash,
                        is_active, is_demo
                    ) VALUES (%s, %s, %s, %s, 'citizen', %s, 1, 0)
                    """,
                    (
                        account_id,
                        request.full_name,
                        request.email,
                        request.mobile,
                        hash_password(request.password),
                    ),
                )
            finally:
                cursor.close()
    except psycopg2.errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    public_user = {
        "id": account_id,
        "name": request.full_name,
        "role": "citizen",
        "department_id": None,
    }
    return {
        "access_token": _create_token(public_user),
        "token_type": "bearer",
        "user": public_user,
    }


@router.get("/me")
def current_session(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "name": user["full_name"],
        "role": user["role"],
        "department_id": user["department_id"],
    }