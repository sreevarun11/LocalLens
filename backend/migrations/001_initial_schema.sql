-- ====================================================================
-- LocalLens PostgreSQL Migration 001: Initial Production Schema
-- Compatible with Supabase PostgreSQL and standard PostgreSQL 14+
-- ====================================================================

-- 1. Users / Accounts
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username VARCHAR(64) UNIQUE,
    email VARCHAR(255),
    password_hash TEXT NOT NULL,
    salt TEXT DEFAULT '',
    display_name VARCHAR(128),
    is_admin BOOLEAN DEFAULT FALSE,
    is_email_verified BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Case-insensitive unique index for usernames
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower ON users (LOWER(username));
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- 2. Profiles (1:1 with users)
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Recovery Codes (Single-use Argon2id hashes)
CREATE TABLE IF NOT EXISTS recovery_codes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_recovery_codes_user ON recovery_codes (user_id);

-- 4. User Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (session_token);

-- 5. User Preferences & Personalization Defaults
CREATE TABLE IF NOT EXISTS user_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    default_profile VARCHAR(32) DEFAULT 'family',
    default_priorities TEXT,
    distance_preferences TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Report Credits & Quota (3 free reports allowance default)
CREATE TABLE IF NOT EXISTS report_credits (
    id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credits_remaining INTEGER DEFAULT 3,
    credits_used INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Search History
CREATE TABLE IF NOT EXISTS search_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    locality_name VARCHAR(255) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    searched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    provider VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_search_history_user ON search_history (user_id);

-- 8. Saved Locations
CREATE TABLE IF NOT EXISTS saved_locations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    locality_name VARCHAR(255) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    label VARCHAR(128),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_saved_locations_user ON saved_locations (user_id);

-- 9. Generated Decision Reports
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    locality_name VARCHAR(255) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    comparison_locality_name VARCHAR(255),
    comparison_lat DOUBLE PRECISION,
    comparison_lng DOUBLE PRECISION,
    user_profile VARCHAR(64),
    user_priorities TEXT,
    sections_included TEXT,
    verification_hash VARCHAR(128) NOT NULL,
    pdf_storage_path TEXT,
    qr_code_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(32) DEFAULT 'completed'
);
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports (user_id);
CREATE INDEX IF NOT EXISTS idx_reports_verification ON reports (verification_hash);

-- 10. Report Data Snapshots (Archival Evidence)
CREATE TABLE IF NOT EXISTS report_data_snapshots (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    raw_evidence TEXT NOT NULL,
    aggregated_metrics TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    providers_used TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_report ON report_data_snapshots (report_id);

-- 11. Property Context Specifics
CREATE TABLE IF NOT EXISTS report_properties (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    property_address TEXT,
    floor_level VARCHAR(64),
    unit_facing VARCHAR(64),
    water_source_declared VARCHAR(64),
    power_backup_declared VARCHAR(64),
    rent_or_price VARCHAR(64),
    user_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_report_properties_report ON report_properties (report_id);

-- 12. Payments (Razorpay Integration)
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    razorpay_order_id VARCHAR(128) UNIQUE NOT NULL,
    razorpay_payment_id VARCHAR(128) UNIQUE,
    razorpay_signature TEXT,
    amount_paise INTEGER NOT NULL,
    amount_inr NUMERIC(10,2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(128) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments (user_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments (razorpay_order_id);

-- 13. User Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    report_id TEXT,
    locality_name VARCHAR(255),
    feedback_type VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. Application Telemetry / Audit Events
CREATE TABLE IF NOT EXISTS app_events (
    id TEXT PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    user_id TEXT,
    metadata TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_app_events_type ON app_events (event_type);
CREATE INDEX IF NOT EXISTS idx_app_events_user ON app_events (user_id);
