
import logging
import os
import re
import sqlite3
<<<<<<< HEAD
=======
import threading
from urllib.parse import urlparse
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import PoolError, ThreadedConnectionPool
from dotenv import load_dotenv


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
LEGACY_DB_PATH = DATA_DIR / "citywatch.db"

load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)
_CONNECTION_POOL = None
_CONNECTION_POOL_LOCK = threading.Lock()


<<<<<<< HEAD
def _normalize_db_name(raw_name: str | None) -> str:
    cleaned = (raw_name or "").strip()

    if not cleaned:
        return "citywatch_ai"

    if cleaned.lower() in {"citywatchai", "citywatch_ai"}:
        return "citywatch_ai"

    # Only permit safe MySQL database identifiers.
    if not re.fullmatch(r"[A-Za-z0-9_]+", cleaned):
        raise ValueError("Invalid MySQL database name in backend/.env.")

    return cleaned


DATABASE_HOST = (
    os.getenv("CITYWATCH_DB_HOST", "127.0.0.1") or "127.0.0.1"
).strip()

DATABASE_PORT = int(
    (os.getenv("CITYWATCH_DB_PORT", "3306") or "3306").strip()
)

DATABASE_USER = (
    os.getenv("CITYWATCH_DB_USER", "root") or "root"
).strip()

DATABASE_PASSWORD = (
    os.getenv("CITYWATCH_DB_PASSWORD", "") or ""
).strip()

DATABASE_NAME = _normalize_db_name(
    os.getenv("CITYWATCH_DB_NAME", "citywatch_ai")
)
=======
DATABASE_HOST = (os.getenv("SUPABASE_DB_HOST", "") or "").strip()

DATABASE_PORT = int((os.getenv("SUPABASE_DB_PORT", "5432") or "5432").strip())

DATABASE_USER = (
    os.getenv("SUPABASE_DB_USER", "postgres") or "postgres"
).strip()

DATABASE_PASSWORD = (
    os.getenv("SUPABASE_DB_PASSWORD", "") or ""
).strip()

DATABASE_NAME = (os.getenv("SUPABASE_DB_NAME", "postgres") or "postgres").strip()
DATABASE_SCHEMA = (os.getenv("SUPABASE_DB_SCHEMA", "citywatch") or "citywatch").strip()
DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
DATABASE_POOL_MAX = max(2, int(os.getenv("DATABASE_POOL_MAX", "8")))
if DATABASE_URL and urlparse(DATABASE_URL).path.strip("/"):
    DATABASE_NAME = urlparse(DATABASE_URL).path.strip("/")

if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", DATABASE_SCHEMA):
    raise ValueError("Invalid SUPABASE_DB_SCHEMA in backend/.env.")
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)


# ============================================================
# STORAGE
# ============================================================

def ensure_storage() -> None:
    """Create the upload directory if it does not exist."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
<<<<<<< HEAD
# MYSQL CONNECTION
# ============================================================

def _connection_settings() -> dict:
    if not DATABASE_USER:
        raise RuntimeError(
            "CITYWATCH_DB_USER is not configured. "
            "Set MySQL connection values in backend/.env."
=======
# POSTGRESQL CONNECTION
# ============================================================

class PostgresConnection:
    def __init__(self, connection, pool):
        self._connection = connection
        self._pool = pool

    def cursor(self, dictionary: bool = False):
        if dictionary:
            return self._connection.cursor(cursor_factory=RealDictCursor)
        return self._connection.cursor()

    def start_transaction(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute("BEGIN")

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        try:
            self._pool.putconn(self._connection, close=bool(self._connection.closed))
        except PoolError:
            self._connection.close()


def _connect() -> PostgresConnection:
    if not DATABASE_URL and not DATABASE_PASSWORD:
        raise RuntimeError(
            "DATABASE_URL or SUPABASE_DB_PASSWORD is not configured."
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
        )
    if not DATABASE_URL and not DATABASE_HOST:
        raise RuntimeError("Set DATABASE_URL or SUPABASE_DB_HOST before starting the backend.")

    global _CONNECTION_POOL
    pool = _CONNECTION_POOL
    if pool is None:
        with _CONNECTION_POOL_LOCK:
            pool = _CONNECTION_POOL
            if pool is None:
                connection_options = dict(
                    sslmode="require",
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=3,
                    options=f"-c search_path={DATABASE_SCHEMA},public",
                    application_name="citywatch-api",
                )
                try:
                    if DATABASE_URL:
                        pool = ThreadedConnectionPool(1, DATABASE_POOL_MAX, DATABASE_URL, **connection_options)
                    else:
                        pool = ThreadedConnectionPool(
                            1,
                            DATABASE_POOL_MAX,
                            host=DATABASE_HOST,
                            port=DATABASE_PORT,
                            user=DATABASE_USER,
                            password=DATABASE_PASSWORD,
                            dbname=DATABASE_NAME,
                            **connection_options,
                        )
                    _CONNECTION_POOL = pool
                except psycopg2.Error as exc:
                    raise RuntimeError(
                        "Unable to connect to Supabase PostgreSQL. "
                        "Check DATABASE_URL or SUPABASE_DB_* settings and Supabase connectivity."
                    ) from exc

    try:
        connection = pool.getconn()
        if connection.closed:
            pool.putconn(connection, close=True)
            connection = pool.getconn()
    except (psycopg2.Error, PoolError) as exc:
        raise RuntimeError("Unable to get a database connection. Check Supabase connectivity and pool limits.") from exc
    return PostgresConnection(connection, pool)


def close_connection_pool() -> None:
    """Close pooled connections during an orderly application shutdown."""
    global _CONNECTION_POOL
    with _CONNECTION_POOL_LOCK:
        if _CONNECTION_POOL is not None:
            _CONNECTION_POOL.closeall()
            _CONNECTION_POOL = None

@contextmanager
<<<<<<< HEAD
def get_connection() -> Iterator[mysql.connector.MySQLConnection]:
    """Provide a MySQL connection with commit and rollback handling."""

    connection = mysql.connector.connect(**_connection_settings())
=======
def get_connection() -> Iterator[PostgresConnection]:
    """Provide a transactional connection to the CityWatch Supabase schema."""
    connection = _connect()
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def ensure_database() -> None:
<<<<<<< HEAD
    """Create the MySQL database if it does not already exist."""

    try:
        connection = mysql.connector.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            charset="utf8mb4",
            connection_timeout=10,
        )

    except mysql.connector.Error as exc:
        raise RuntimeError(
            "Unable to connect to MySQL. "
            "Check your backend/.env settings and MySQL Server."
        ) from exc

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}`
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )

=======
    """Ensure the backend's isolated schema exists in the Supabase database."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"')
            connection.commit()
        finally:
            cursor.close()
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
    finally:
        connection.close()


# ============================================================
# LEGACY SQLITE MIGRATION
# ============================================================

def _migrate_legacy_sqlite(
<<<<<<< HEAD
    connection: mysql.connector.MySQLConnection
=======
    connection: PostgresConnection
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
) -> None:
    """
    Import existing complaints from the old SQLite database.

    Latitude and longitude are intentionally excluded.
    The location field is preserved.

    Optional SQLite fields are handled safely.
<<<<<<< HEAD
    Existing MySQL complaint IDs are not duplicated.
=======
    Existing PostgreSQL complaint IDs are not duplicated.
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
    """

    if not LEGACY_DB_PATH.exists():
        logger.info("No legacy SQLite database found. Skipping migration.")
        return

    logger.info("Checking legacy SQLite complaint records...")

    try:
        with sqlite3.connect(LEGACY_DB_PATH) as legacy_connection:

            legacy_connection.row_factory = sqlite3.Row

            table = legacy_connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'complaints'
                """
            ).fetchone()

            if table is None:
                logger.info(
                    "No complaints table found in legacy SQLite database."
                )
                return

            # Read actual SQLite column names.
            column_info = legacy_connection.execute(
                "PRAGMA table_info(complaints)"
            ).fetchall()

            available_columns = {
                column["name"] for column in column_info
            }

            # These fields are needed for a useful complaint record.
            required_columns = {
                "id",
                "title",
                "category",
                "location",
                "description",
                "priority",
                "status",
                "created_at",
                "updated_at",
            }

            missing_columns = required_columns - available_columns

            if missing_columns:
                raise RuntimeError(
                    "Legacy SQLite complaints table is missing required "
                    f"columns: {', '.join(sorted(missing_columns))}"
                )

            # Fetch complete rows without referring to removed columns.
            rows = legacy_connection.execute(
                "SELECT * FROM complaints"
            ).fetchall()

            if not rows:
                logger.info("No legacy complaints to migrate.")
                return

            def get_value(row, column, default=None):
                if column in available_columns:
                    return row[column]

                return default

<<<<<<< HEAD
            # Match exactly 11 MySQL columns and 11 values.
=======
            # Map the legacy SQLite complaint row into the current PostgreSQL schema.
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
            migration_values = []

            for row in rows:
                migration_values.append(
                    (
                        row["id"],
                        row["title"],
                        row["category"],
                        row["location"] or "",
                        row["description"] or "",
                        get_value(row, "video_name"),
                        get_value(row, "video_path"),
                        get_value(row, "priority", "Needs Review")
                        or "Needs Review",
                        get_value(row, "status", "Submitted")
                        or "Submitted",
                        row["created_at"],
                        row["updated_at"],
                    )
                )

<<<<<<< HEAD
        # Insert legacy records into MySQL.
=======
        # Insert legacy records into PostgreSQL.
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
        cursor = connection.cursor()

        try:
            cursor.executemany(
                """
<<<<<<< HEAD
                INSERT IGNORE INTO complaints (
=======
                INSERT INTO complaints (
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
                    id,
                    title,
                    category,
                    location,
                    description,
                    video_name,
                    video_path,
                    priority,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
<<<<<<< HEAD
=======
                ON CONFLICT (id) DO NOTHING
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
                """,
                migration_values,
            )

            logger.info(
                "Legacy migration completed. "
                "Inserted %s complaint row(s).",
                cursor.rowcount,
            )

        finally:
            cursor.close()

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Unable to read legacy SQLite database: {exc}"
        ) from exc


# ============================================================
<<<<<<< HEAD
# MYSQL SCHEMA HELPERS
=======
# POSTGRESQL SCHEMA HELPERS
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
# ============================================================

def _ensure_complaint_column(
    cursor,
    column_name: str,
    column_definition: str,
) -> None:
    """Add a complaint column only when it does not exist."""

    allowed_columns = {
        "assigned_department_id",
        "assigned_officer_id",
        "due_date",
        "assignment_instructions",
        "created_by_user_id",
    }

    if column_name not in allowed_columns:
        raise ValueError(
            f"Unsupported complaint column: {column_name}"
        )

    cursor.execute(
        """
        SELECT COUNT(*) AS column_count
<<<<<<< HEAD
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'complaints'
          AND COLUMN_NAME = %s
=======
                FROM information_schema.columns
                WHERE table_schema = %s
                    AND table_name = 'complaints'
                    AND column_name = %s
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
        """,
                (DATABASE_SCHEMA, column_name),
    )

    result = cursor.fetchone()

    if result[0] == 0:
        cursor.execute(
            f"""
            ALTER TABLE complaints
            ADD COLUMN {column_name} {column_definition}
            """
        )

        logger.info("Added missing complaints column: %s", column_name)


<<<<<<< HEAD
=======
def _ensure_complaint_foreign_keys(cursor) -> None:
    """Add forward-only complaint references without rejecting older orphan rows."""
    constraints = (
        ("complaints_created_by_user_fk", "created_by_user_id", "users(id)"),
        ("complaints_assigned_department_fk", "assigned_department_id", "departments(id)"),
        ("complaints_assigned_officer_fk", "assigned_officer_id", "users(id)"),
    )
    for constraint_name, column_name, target in constraints:
        cursor.execute(
            "SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = 'complaints'::regclass",
            (constraint_name,),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            f"ALTER TABLE complaints ADD CONSTRAINT {constraint_name} "
            f"FOREIGN KEY ({column_name}) REFERENCES {target} NOT VALID"
        )


>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)
# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db() -> None:
    """
<<<<<<< HEAD
    Initialize CityWatch AI MySQL tables.
=======
    Initialize CityWatch AI PostgreSQL tables.
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)

    This function is safe to call on application startup.
    Existing tables and complaint records are preserved.
    """

    logger.info("Initializing CityWatch AI database...")

<<<<<<< HEAD
    ensure_storage()
    ensure_database()

    with get_connection() as connection:

        cursor = connection.cursor()

        try:

            # ------------------------------------------------
            # COMPLAINTS
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (

                    id VARCHAR(40) PRIMARY KEY,

                    title VARCHAR(255) NOT NULL,

                    category VARCHAR(100) NOT NULL,

                    location VARCHAR(500) NOT NULL DEFAULT '',

                    description TEXT NOT NULL,

                    video_name VARCHAR(255) NULL,

                    video_path VARCHAR(500) NULL,

                    priority VARCHAR(50)
                        NOT NULL DEFAULT 'Needs Review',

                    status VARCHAR(50)
                        NOT NULL DEFAULT 'Submitted',

                    created_at VARCHAR(40) NOT NULL,

                    updated_at VARCHAR(40) NOT NULL,

                    INDEX idx_complaints_created_at (created_at),

                    INDEX idx_complaints_status (status)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # DEPARTMENTS
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (

                    id CHAR(36) PRIMARY KEY,

                    name VARCHAR(120) NOT NULL UNIQUE,

                    is_active TINYINT(1)
                        NOT NULL DEFAULT 1,

                    created_at TIMESTAMP
                        NOT NULL DEFAULT CURRENT_TIMESTAMP

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # EVIDENCE FILES
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_files (

                    id CHAR(36) PRIMARY KEY,

                    complaint_id VARCHAR(40) NOT NULL,

                    original_name VARCHAR(255) NOT NULL,

                    file_type VARCHAR(10) NOT NULL,

                    mime_type VARCHAR(100) NOT NULL,

                    file_size BIGINT NOT NULL,

                    file_path VARCHAR(500) NOT NULL,

                    uploaded_by VARCHAR(40) NOT NULL,

                    created_at DATETIME NOT NULL,

                    INDEX idx_evidence_complaint_created (
                        complaint_id,
                        created_at
                    ),

                    CONSTRAINT fk_evidence_complaint
                        FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # AI ANALYSES
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_analyses (

                    id BIGINT AUTO_INCREMENT PRIMARY KEY,

                    complaint_id VARCHAR(40) NOT NULL,

                    model_name VARCHAR(100) NOT NULL,

                    model_version VARCHAR(100) NULL,

                    analysis_status VARCHAR(40) NOT NULL,

                    predicted_category VARCHAR(100) NULL,

                    confidence DECIMAL(7, 6) NULL,

                    predictions JSON NOT NULL,

                    summary TEXT NOT NULL,

                    error_message TEXT NULL,

                    processing_time_ms INT NOT NULL DEFAULT 0,

                    created_at DATETIME NOT NULL,

                    INDEX idx_ai_analyses_complaint_created (
                        complaint_id,
                        created_at
                    ),

                    CONSTRAINT fk_ai_analysis_complaint
                        FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # USERS
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (

                    id VARCHAR(40) PRIMARY KEY,

                    full_name VARCHAR(120) NOT NULL,

                    role VARCHAR(20) NOT NULL,

                    department_id CHAR(36) NULL,

                    password_hash VARCHAR(255) NOT NULL,

                    is_active TINYINT(1) NOT NULL DEFAULT 1,

                    is_demo TINYINT(1) NOT NULL DEFAULT 0,

                    created_at TIMESTAMP
                        NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    INDEX idx_users_role_department (
                        role,
                        department_id,
                        is_active
                    ),

                    CONSTRAINT fk_users_department
                        FOREIGN KEY (department_id)
                        REFERENCES departments(id)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # ASSIGNMENTS
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS assignments (

                    id CHAR(36) PRIMARY KEY,

                    complaint_id VARCHAR(40) NOT NULL,

                    department_id CHAR(36) NOT NULL,

                    officer_id VARCHAR(40) NOT NULL,

                    assigned_by VARCHAR(40) NOT NULL,

                    assigned_at DATETIME NOT NULL,

                    due_date DATE NULL,

                    instructions TEXT NULL,

                    reassignment_reason TEXT NULL,

                    is_active TINYINT(1) NOT NULL DEFAULT 1,

                    INDEX idx_assignments_officer_active (
                        officer_id,
                        is_active,
                        assigned_at
                    ),

                    INDEX idx_assignments_complaint_active (
                        complaint_id,
                        is_active
                    ),

                    CONSTRAINT fk_assignments_complaint
                        FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id),

                    CONSTRAINT fk_assignments_department
                        FOREIGN KEY (department_id)
                        REFERENCES departments(id),

                    CONSTRAINT fk_assignments_officer
                        FOREIGN KEY (officer_id)
                        REFERENCES users(id),

                    CONSTRAINT fk_assignments_assigner
                        FOREIGN KEY (assigned_by)
                        REFERENCES users(id)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # COMPLAINT HISTORY
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS complaint_history (

                    id BIGINT AUTO_INCREMENT PRIMARY KEY,

                    complaint_id VARCHAR(40) NOT NULL,

                    actor_id VARCHAR(40) NOT NULL,

                    old_status VARCHAR(50) NULL,

                    new_status VARCHAR(50) NULL,

                    action VARCHAR(60) NOT NULL,

                    reason TEXT NULL,

                    metadata JSON NULL,

                    created_at DATETIME NOT NULL,

                    INDEX idx_history_complaint_created (
                        complaint_id,
                        created_at
                    ),

                    CONSTRAINT fk_history_complaint
                        FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id),

                    CONSTRAINT fk_history_actor
                        FOREIGN KEY (actor_id)
                        REFERENCES users(id)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # NOTIFICATIONS
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (

                    id CHAR(36) PRIMARY KEY,

                    recipient_id VARCHAR(40) NOT NULL,

                    complaint_id VARCHAR(40) NOT NULL,

                    title VARCHAR(160) NOT NULL,

                    message TEXT NOT NULL,

                    is_read TINYINT(1) NOT NULL DEFAULT 0,

                    created_at DATETIME NOT NULL,

                    INDEX idx_notifications_recipient_read (
                        recipient_id,
                        is_read,
                        created_at
                    ),

                    CONSTRAINT fk_notifications_recipient
                        FOREIGN KEY (recipient_id)
                        REFERENCES users(id),

                    CONSTRAINT fk_notifications_complaint
                        FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # ------------------------------------------------
            # ADDITIONAL COMPLAINT COLUMNS
            # ------------------------------------------------

            _ensure_complaint_column(
                cursor,
                "assigned_department_id",
                "CHAR(36) NULL",
            )

            _ensure_complaint_column(
                cursor,
                "assigned_officer_id",
                "VARCHAR(40) NULL",
            )

            _ensure_complaint_column(
                cursor,
                "due_date",
                "DATE NULL",
            )

            _ensure_complaint_column(
                cursor,
                "assignment_instructions",
                "TEXT NULL",
            )

            _ensure_complaint_column(
                cursor,
                "created_by_user_id",
                "VARCHAR(40) NULL",
            )

        finally:
            cursor.close()

        # Migrate old SQLite complaints after MySQL tables exist.
        _migrate_legacy_sqlite(connection)
=======
    ensure_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            schema_path = BASE_DIR / "database" / "citywatch_schema.sql"
            schema_sql = schema_path.read_text(encoding="utf-8")
            for statement in schema_sql.split(";"):
                if statement.strip():
                    cursor.execute(statement)

            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(254)")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(32)")
            cursor.execute("ALTER TABLE evidence_files ADD COLUMN IF NOT EXISTS sha256 CHAR(64)")
            cursor.execute("ALTER TABLE evidence_files ADD COLUMN IF NOT EXISTS perceptual_hash CHAR(16)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON evidence_files (sha256) "
                "WHERE sha256 IS NOT NULL"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS complaint_supports ("
                "supporting_complaint_id VARCHAR(40) PRIMARY KEY REFERENCES complaints(id), "
                "canonical_complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id), "
                "supported_by_user_id VARCHAR(40) NOT NULL REFERENCES users(id), "
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "CHECK (supporting_complaint_id <> canonical_complaint_id))"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_complaint_supports_canonical "
                "ON complaint_supports (canonical_complaint_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON evidence_files (sha256) "
                "WHERE sha256 IS NOT NULL"
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
                ON users (LOWER(email))
                WHERE email IS NOT NULL
                """
            )

            for column_name, column_definition in (
                ("assigned_department_id", "CHAR(36) NULL"),
                ("assigned_officer_id", "VARCHAR(40) NULL"),
                ("due_date", "DATE NULL"),
                ("assignment_instructions", "TEXT NULL"),
                ("created_by_user_id", "VARCHAR(40) NULL"),
            ):
                _ensure_complaint_column(cursor, column_name, column_definition)
            _ensure_complaint_foreign_keys(cursor)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_complaints_created_by_user "
                "ON complaints (created_by_user_id, created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_sha256 "
                "ON evidence_files (sha256) WHERE sha256 IS NOT NULL"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_complaints_status_normalized_created "
                "ON complaints (LOWER(REPLACE(TRIM(status), '_', ' ')), created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_complaints_assigned_officer_status "
                "ON complaints (assigned_officer_id, LOWER(TRIM(status)), created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_complaints_assigned_department_status "
                "ON complaints (assigned_department_id, LOWER(TRIM(status)), created_at DESC)"
            )
        finally:
            cursor.close()

        # Legacy imports are explicit so a production deploy never silently changes data.
        if os.getenv("CITYWATCH_IMPORT_LEGACY_SQLITE", "false").lower() == "true":
            _migrate_legacy_sqlite(connection)
>>>>>>> 334704a (Update CityWatch AI with duplicate detection and Supabase integration)

    logger.info("CityWatch AI database initialized successfully.")
