import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import mysql.connector
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
LEGACY_DB_PATH = DATA_DIR / "citywatch.db"

load_dotenv(BASE_DIR / ".env")


def _normalize_db_name(raw_name: str | None) -> str:
    cleaned = (raw_name or "").strip()
    if not cleaned:
        return "citywatch_ai"

    normalized = cleaned.strip()
    if normalized.lower() in {"citywatchai", "citywatch_ai"}:
        return "citywatch_ai"
    return normalized


DATABASE_HOST = (os.getenv("CITYWATCH_DB_HOST", "127.0.0.1") or "127.0.0.1").strip()
DATABASE_PORT = int((os.getenv("CITYWATCH_DB_PORT", "3306") or "3306").strip())
DATABASE_USER = (os.getenv("CITYWATCH_DB_USER", "root") or "root").strip()
DATABASE_PASSWORD = (os.getenv("CITYWATCH_DB_PASSWORD", "") or "").strip()
DATABASE_NAME = _normalize_db_name(os.getenv("CITYWATCH_DB_NAME", "citywatch_ai"))

logger = logging.getLogger(__name__)


def ensure_storage() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _connection_settings() -> dict:
    if not DATABASE_USER:
        raise RuntimeError(
            "CITYWATCH_DB_USER is not configured. Set the MySQL connection "
            "values in backend/.env."
        )

    return {
        "host": DATABASE_HOST,
        "port": DATABASE_PORT,
        "user": DATABASE_USER,
        "password": DATABASE_PASSWORD,
        "database": DATABASE_NAME,
        "charset": "utf8mb4",
        "connection_timeout": 10,
    }


@contextmanager
def get_connection() -> Iterator[mysql.connector.MySQLConnection]:
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
            "Unable to connect to MySQL to initialize citywatch_ai database. "
            "Check the values in backend/.env."
        ) from exc

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        connection.close()


def _migrate_legacy_sqlite(connection: mysql.connector.MySQLConnection) -> None:
    if not LEGACY_DB_PATH.exists():
        return

    with sqlite3.connect(LEGACY_DB_PATH) as legacy_connection:
        legacy_connection.row_factory = sqlite3.Row
        table = legacy_connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'complaints'"
        ).fetchone()
        if table is None:
            return

        rows = legacy_connection.execute(
            """
            SELECT id, title, category, location, latitude, longitude, description,
                   video_name, video_path, priority, status, created_at, updated_at
            FROM complaints
            """
        ).fetchall()

    if not rows:
        return

    cursor = connection.cursor()
    try:
        cursor.executemany(
            """
            INSERT IGNORE INTO complaints (
                id, title, category, location, latitude, longitude, description,
                video_name, video_path, priority, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row["id"],
                    row["title"],
                    row["category"],
                    row["location"],
                    row["latitude"],
                    row["longitude"],
                    row["description"],
                    row["video_name"],
                    row["video_path"],
                    row["priority"],
                    row["status"],
                    row["created_at"],
                    row["updated_at"],
                )
                for row in rows
            ],
        )
        logger.info("Imported %s legacy complaint row(s) from SQLite.", cursor.rowcount)
    finally:
        cursor.close()


def init_db() -> None:
    ensure_storage()
    ensure_database()
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (
                    id VARCHAR(40) PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    location VARCHAR(500) NOT NULL DEFAULT '',
                    latitude DOUBLE NULL,
                    longitude DOUBLE NULL,
                    description TEXT NOT NULL,
                    video_name VARCHAR(255) NULL,
                    video_path VARCHAR(500) NULL,
                    priority VARCHAR(50) NOT NULL DEFAULT 'Needs Review',
                    status VARCHAR(50) NOT NULL DEFAULT 'Submitted',
                    created_at VARCHAR(40) NOT NULL,
                    updated_at VARCHAR(40) NOT NULL,
                    INDEX idx_complaints_created_at (created_at),
                    INDEX idx_complaints_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id CHAR(36) PRIMARY KEY,
                    name VARCHAR(120) NOT NULL UNIQUE,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
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
                    INDEX idx_evidence_complaint_created (complaint_id, created_at),
                    CONSTRAINT fk_evidence_complaint FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
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
                    INDEX idx_ai_analyses_complaint_created (complaint_id, created_at),
                    CONSTRAINT fk_ai_analysis_complaint FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
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
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_users_role_department (role, department_id, is_active),
                    CONSTRAINT fk_users_department FOREIGN KEY (department_id)
                        REFERENCES departments(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
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
                    INDEX idx_assignments_officer_active (officer_id, is_active, assigned_at),
                    INDEX idx_assignments_complaint_active (complaint_id, is_active),
                    CONSTRAINT fk_assignments_complaint FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id),
                    CONSTRAINT fk_assignments_department FOREIGN KEY (department_id)
                        REFERENCES departments(id),
                    CONSTRAINT fk_assignments_officer FOREIGN KEY (officer_id)
                        REFERENCES users(id),
                    CONSTRAINT fk_assignments_assigner FOREIGN KEY (assigned_by)
                        REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
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
                    INDEX idx_history_complaint_created (complaint_id, created_at),
                    CONSTRAINT fk_history_complaint FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id),
                    CONSTRAINT fk_history_actor FOREIGN KEY (actor_id)
                        REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
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
                    INDEX idx_notifications_recipient_read (recipient_id, is_read, created_at),
                    CONSTRAINT fk_notifications_recipient FOREIGN KEY (recipient_id)
                        REFERENCES users(id),
                    CONSTRAINT fk_notifications_complaint FOREIGN KEY (complaint_id)
                        REFERENCES complaints(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            _ensure_complaint_column(cursor, "assigned_department_id", "CHAR(36) NULL")
            _ensure_complaint_column(cursor, "assigned_officer_id", "VARCHAR(40) NULL")
            _ensure_complaint_column(cursor, "due_date", "DATE NULL")
            _ensure_complaint_column(cursor, "assignment_instructions", "TEXT NULL")
            _ensure_complaint_column(cursor, "created_by_user_id", "VARCHAR(40) NULL")
        finally:
            cursor.close()

        _migrate_legacy_sqlite(connection)


def _ensure_complaint_column(cursor, column_name: str, column_definition: str) -> None:
    cursor.execute(
        """
        SELECT COUNT(*) AS column_count
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'complaints' AND COLUMN_NAME = %s
        """,
        (DATABASE_NAME, column_name),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(f"ALTER TABLE complaints ADD COLUMN {column_name} {column_definition}")
