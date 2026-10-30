CREATE SCHEMA IF NOT EXISTS citywatch;
SET search_path TO citywatch, public;

CREATE TABLE IF NOT EXISTS complaints (
    id VARCHAR(40) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    location VARCHAR(500) NOT NULL DEFAULT '',
    latitude DOUBLE PRECISION NULL,
    longitude DOUBLE PRECISION NULL,
    description TEXT NOT NULL,
    video_name VARCHAR(255) NULL,
    video_path VARCHAR(500) NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'Needs Review',
    status VARCHAR(50) NOT NULL DEFAULT 'Submitted',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    assigned_department_id CHAR(36) NULL,
    assigned_officer_id VARCHAR(40) NULL,
    due_date DATE NULL,
    assignment_instructions TEXT NULL,
    created_by_user_id VARCHAR(40) NULL
);

CREATE TABLE IF NOT EXISTS departments (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    is_active SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence_files (
    id CHAR(36) PRIMARY KEY,
    complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id),
    original_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    uploaded_by VARCHAR(40) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    sha256 CHAR(64) NULL,
    perceptual_hash CHAR(16) NULL
);

CREATE TABLE IF NOT EXISTS ai_analyses (
    id BIGSERIAL PRIMARY KEY,
    complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(100) NULL,
    analysis_status VARCHAR(40) NOT NULL,
    predicted_category VARCHAR(100) NULL,
    confidence DECIMAL(7, 6) NULL,
    predictions JSONB NOT NULL,
    summary TEXT NOT NULL,
    error_message TEXT NULL,
    processing_time_ms INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(40) PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NULL,
    phone VARCHAR(32) NULL,
    role VARCHAR(20) NOT NULL,
    department_id CHAR(36) NULL REFERENCES departments(id),
    password_hash VARCHAR(255) NOT NULL,
    is_active SMALLINT NOT NULL DEFAULT 1,
    is_demo SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaint_supports (
    supporting_complaint_id VARCHAR(40) PRIMARY KEY REFERENCES complaints(id),
    canonical_complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id),
    supported_by_user_id VARCHAR(40) NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (supporting_complaint_id <> canonical_complaint_id)
);

CREATE TABLE IF NOT EXISTS assignments (
    id CHAR(36) PRIMARY KEY,
    complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id),
    department_id CHAR(36) NOT NULL REFERENCES departments(id),
    officer_id VARCHAR(40) NOT NULL REFERENCES users(id),
    assigned_by VARCHAR(40) NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMP NOT NULL,
    due_date DATE NULL,
    instructions TEXT NULL,
    reassignment_reason TEXT NULL,
    is_active SMALLINT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS complaint_history (
    id BIGSERIAL PRIMARY KEY,
    complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id),
    actor_id VARCHAR(40) NOT NULL REFERENCES users(id),
    old_status VARCHAR(50) NULL,
    new_status VARCHAR(50) NULL,
    action VARCHAR(60) NOT NULL,
    reason TEXT NULL,
    metadata JSONB NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id CHAR(36) PRIMARY KEY,
    recipient_id VARCHAR(40) NOT NULL REFERENCES users(id),
    complaint_id VARCHAR(40) NOT NULL REFERENCES complaints(id),
    title VARCHAR(160) NOT NULL,
    message TEXT NOT NULL,
    is_read SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(254);
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(32);
ALTER TABLE evidence_files ADD COLUMN IF NOT EXISTS sha256 CHAR(64);
ALTER TABLE evidence_files ADD COLUMN IF NOT EXISTS perceptual_hash CHAR(16);
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_department_id CHAR(36) NULL;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_officer_id VARCHAR(40) NULL;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS due_date DATE NULL;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assignment_instructions TEXT NULL;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS created_by_user_id VARCHAR(40) NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'complaints_created_by_user_fk' AND conrelid = 'citywatch.complaints'::regclass) THEN
        ALTER TABLE citywatch.complaints ADD CONSTRAINT complaints_created_by_user_fk FOREIGN KEY (created_by_user_id) REFERENCES citywatch.users(id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'complaints_assigned_department_fk' AND conrelid = 'citywatch.complaints'::regclass) THEN
        ALTER TABLE citywatch.complaints ADD CONSTRAINT complaints_assigned_department_fk FOREIGN KEY (assigned_department_id) REFERENCES citywatch.departments(id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'complaints_assigned_officer_fk' AND conrelid = 'citywatch.complaints'::regclass) THEN
        ALTER TABLE citywatch.complaints ADD CONSTRAINT complaints_assigned_officer_fk FOREIGN KEY (assigned_officer_id) REFERENCES citywatch.users(id) NOT VALID;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_complaints_created_at ON complaints (created_at);
CREATE INDEX IF NOT EXISTS idx_complaints_created_by_user ON complaints (created_by_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints (status);
CREATE INDEX IF NOT EXISTS idx_complaints_status_normalized_created ON complaints (LOWER(REPLACE(TRIM(status), '_', ' ')), created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_assigned_officer_status ON complaints (assigned_officer_id, LOWER(TRIM(status)), created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_assigned_department_status ON complaints (assigned_department_id, LOWER(TRIM(status)), created_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON evidence_files (sha256) WHERE sha256 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_complaint_supports_canonical ON complaint_supports (canonical_complaint_id);
CREATE INDEX IF NOT EXISTS idx_evidence_complaint_created ON evidence_files (complaint_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_analyses_complaint_created ON ai_analyses (complaint_id, created_at);
CREATE INDEX IF NOT EXISTS idx_users_role_department ON users (role, department_id, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users (LOWER(email)) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_assignments_officer_active ON assignments (officer_id, is_active, assigned_at);
CREATE INDEX IF NOT EXISTS idx_assignments_complaint_active ON assignments (complaint_id, is_active);
CREATE INDEX IF NOT EXISTS idx_history_complaint_created ON complaint_history (complaint_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient_read ON notifications (recipient_id, is_read, created_at);
-- Evidence objects stay private; the backend accesses them with the service-role key.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('evidence', 'evidence', FALSE, 52428800, ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/ogg'])
ON CONFLICT (id) DO UPDATE SET public = FALSE, file_size_limit = EXCLUDED.file_size_limit, allowed_mime_types = EXCLUDED.allowed_mime_types;
