"""PostgreSQL database access for CityWatch AI (Supabase-compatible)."""

from __future__ import annotations

import logging
import os
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import PoolError, ThreadedConnectionPool
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
LEGACY_DB_PATH = DATA_DIR / "citywatch.db"

load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger(__name__)

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
DATABASE_HOST = (os.getenv("SUPABASE_DB_HOST") or "").strip()
DATABASE_PORT = int((os.getenv("SUPABASE_DB_PORT", "5432") or "5432").strip())
DATABASE_USER = (os.getenv("SUPABASE_DB_USER", "postgres") or "postgres").strip()
DATABASE_PASSWORD = (os.getenv("SUPABASE_DB_PASSWORD") or "").strip()
DATABASE_NAME = (os.getenv("SUPABASE_DB_NAME", "postgres") or "postgres").strip()
DATABASE_SCHEMA = (os.getenv("SUPABASE_DB_SCHEMA", "citywatch") or "citywatch").strip()
DATABASE_POOL_MIN = max(1, int(os.getenv("DATABASE_POOL_MIN", "1")))
DATABASE_POOL_MAX = max(DATABASE_POOL_MIN, int(os.getenv("DATABASE_POOL_MAX", "8")))

if DATABASE_URL:
    parsed_url = urlparse(DATABASE_URL)
    if parsed_url.path.strip("/"):
        DATABASE_NAME = parsed_url.path.strip("/")

if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", DATABASE_SCHEMA):
    raise ValueError("Invalid SUPABASE_DB_SCHEMA. Use a simple PostgreSQL schema name.")

_CONNECTION_POOL: ThreadedConnectionPool | None = None
_CONNECTION_POOL_LOCK = threading.Lock()


class PostgresConnection:
    """Small compatibility wrapper for routes written with cursor(dictionary=True)."""

    def __init__(self, raw_connection, pool: ThreadedConnectionPool):
        self._connection = raw_connection
        self._pool = pool

    def cursor(self, dictionary: bool = False):
        if dictionary:
            return self._connection.cursor(cursor_factory=RealDictCursor)
        return self._connection.cursor()

    def start_transaction(self) -> None:
        # psycopg2 starts a transaction automatically on the first statement.
        # This method preserves compatibility with existing route handlers.
        if self._connection.autocommit:
            self._connection.autocommit = False

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        try:
            if self._connection.closed:
                self._pool.putconn(self._connection, close=True)
            else:
                # Ensure a clean connection is returned to the pool.
                self._pool.putconn(self._connection)
        except PoolError:
            try:
                self._connection.close()
            except Exception:
                pass


def _connection_parameters() -> dict:
    common = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "15")),
        "application_name": "citywatch-api",
        "options": f"-c search_path={DATABASE_SCHEMA},public",
    }
    # Supabase requires TLS. DATABASE_URL can include sslmode already; sslmode=require
    # is also supplied explicitly for direct host/user/password configuration.
    if DATABASE_URL:
        return {"dsn": DATABASE_URL, "sslmode": "require", **common}
    if not DATABASE_HOST or not DATABASE_PASSWORD:
        raise RuntimeError(
            "Database configuration is missing. Set DATABASE_URL, or set "
            "SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD in the backend environment."
        )
    return {
        "host": DATABASE_HOST,
        "port": DATABASE_PORT,
        "user": DATABASE_USER,
        "password": DATABASE_PASSWORD,
        "dbname": DATABASE_NAME,
        "sslmode": "require",
        **common,
    }


def _get_pool() -> ThreadedConnectionPool:
    global _CONNECTION_POOL
    if _CONNECTION_POOL is None:
        with _CONNECTION_POOL_LOCK:
            if _CONNECTION_POOL is None:
                try:
                    _CONNECTION_POOL = ThreadedConnectionPool(
                        DATABASE_POOL_MIN,
                        DATABASE_POOL_MAX,
                        **_connection_parameters(),
                    )
                    logger.info("PostgreSQL connection pool initialized.")
                except psycopg2.Error as exc:
                    raise RuntimeError(
                        "Unable to connect to PostgreSQL. Check DATABASE_URL or SUPABASE_DB_* settings."
                    ) from exc
    return _CONNECTION_POOL


def _connect() -> PostgresConnection:
    pool = _get_pool()
    try:
        raw = pool.getconn()
        if raw.closed:
            pool.putconn(raw, close=True)
            raw = pool.getconn()
        return PostgresConnection(raw, pool)
    except (psycopg2.Error, PoolError) as exc:
        raise RuntimeError("Unable to obtain a PostgreSQL connection from the pool.") from exc


@contextmanager
def get_connection() -> Iterator[PostgresConnection]:
    """Yield a connection; commit on success, rollback on error, then return it."""
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def close_connection_pool() -> None:
    """Close all pooled connections during application shutdown."""
    global _CONNECTION_POOL
    with _CONNECTION_POOL_LOCK:
        if _CONNECTION_POOL is not None:
            _CONNECTION_POOL.closeall()
            _CONNECTION_POOL = None


def ensure_storage() -> None:
    """Create the local temporary upload directory if legacy code expects it."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ensure_database() -> None:
    """Ensure the configured application schema exists in the PostgreSQL database."""
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            # DATABASE_SCHEMA has already been validated against an identifier allowlist.
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"')
        finally:
            cursor.close()


def init_db() -> None:
    """Create/update tables and indexes from backend/database/citywatch_schema.sql."""
    ensure_storage()
    schema_file = BASE_DIR / "database" / "citywatch_schema.sql"
    if not schema_file.is_file():
        raise RuntimeError(f"Database schema file not found: {schema_file}")

    sql_text = schema_file.read_text(encoding="utf-8")
    ensure_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            # The provided schema file contains simple DDL statements separated by ';'.
            # It does not contain procedural blocks or semicolons inside string literals.
            for statement in sql_text.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            logger.info("CityWatch AI PostgreSQL schema initialized successfully.")
        finally:
            cursor.close()
