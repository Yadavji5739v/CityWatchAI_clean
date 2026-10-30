
import logging
import os
import re
import sqlite3

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


# ============================================================
# STORAGE
# ============================================================

def ensure_storage() -> None:
    """Create the upload directory if it does not exist."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# MYSQL CONNECTION
# ============================================================

def _connection_settings() -> dict:
    if not DATABASE_USER:
        raise RuntimeError(
            "CITYWATCH_DB_USER is not configured. "
            "Set MySQL connection values in backend/.env."
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
def get_connection() -> Iterator[mysql.connector.MySQLConnection]:
    """Provide a MySQL connection with commit and rollback handling."""

    connection = mysql.connector.connect(**_connection_settings())

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def ensure_database() -> None:
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

    finally:
        connection.close()


# ============================================================
# LEGACY SQLITE MIGRATION
# ============================================================

def _migrate_legacy_sqlite(
    connection: mysql.connector.MySQLConnection
) -> None:
    """
    Import existing complaints from the old SQLite database.

    Latitude and longitude are intentionally excluded.
    The location field is preserved.

    Optional SQLite fields are handled safely.
    Existing MySQL complaint IDs are not duplicated.
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

            # Match exactly 11 MySQL columns and 11 values.
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

        # Insert legacy records into MySQL.
        cursor = connection.cursor()

        try:
            cursor.executemany(
                """
                INSERT IGNORE INTO complaints (
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
# MYSQL SCHEMA HELPERS
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
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'complaints'
          AND COLUMN_NAME = %s
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


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db() -> None:
    """
    Initialize CityWatch AI MySQL tables.

    This function is safe to call on application startup.
    Existing tables and complaint records are preserved.
    """

    logger.info("Initializing CityWatch AI database...")

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

    logger.info("CityWatch AI database initialized successfully.")
