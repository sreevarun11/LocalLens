import sqlite3
import os
import re
import json
import uuid
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

from backend.app.auth.argon2_utils import hash_secret, verify_secret
from backend.app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "locallens_dev.db")
MIGRATION_SQL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "migrations", "001_initial_schema.sql")

def get_database_mode() -> str:
    """Returns 'postgresql' or 'sqlite' depending on configuration."""
    if settings.DATABASE_URL:
        return "postgresql"
    return "sqlite"

class PostgresCursorWrapper:
    """
    Wraps psycopg2 DictCursor to provide 100% parameter compatibility with SQLite (? -> %s)
    and identical dictionary/index row access.
    """
    def __init__(self, pg_cursor):
        self._cursor = pg_cursor

    def execute(self, query: str, params: Any = None):
        # Convert SQLite ? placeholders to psycopg2 %s placeholders
        if params is not None:
            translated_query = re.sub(r'(?<!\?)\?(?!\?)', '%s', query)
            return self._cursor.execute(translated_query, params)
        else:
            return self._cursor.execute(query)

    def executemany(self, query: str, seq_of_params):
        translated_query = re.sub(r'(?<!\?)\?(?!\?)', '%s', query)
        return self._cursor.executemany(translated_query, seq_of_params)

    def executescript(self, sql_script: str):
        return self._cursor.execute(sql_script)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

class PostgresConnectionWrapper:
    """
    Wraps psycopg2 Connection to provide cursor() with DictCursor row factory and ? query translation.
    """
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self):
        import psycopg2.extras
        pg_cursor = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(pg_cursor)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

def get_connection():
    """
    Returns an active database connection.
    Connects to PostgreSQL target when DATABASE_URL is set.
    Fails loudly in production if PostgreSQL cannot be reached (no silent fallback).
    Uses local SQLite for development when DATABASE_URL is not set.
    """
    db_mode = get_database_mode()
    if db_mode == "postgresql":
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(settings.DATABASE_URL)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            if settings.ENVIRONMENT == "production":
                logger.critical(f"FATAL: Production PostgreSQL connection failed: {e}")
                raise RuntimeError(f"Production database connection failed: {e}") from e
            else:
                logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite for development.")

    # SQLite connection for local development
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash password using Argon2id."""
    return hash_secret(password), ""

def verify_password(password: str, password_hash: str, salt: str = "") -> bool:
    """Verify password supporting Argon2id and legacy PBKDF2."""
    if password_hash.startswith("$argon2"):
        return verify_secret(password_hash, password)
    if salt:
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(key.hex(), password_hash)
    return False

def init_db():
    db_mode = get_database_mode()
    if db_mode == "postgresql":
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if os.path.exists(MIGRATION_SQL_PATH):
                with open(MIGRATION_SQL_PATH, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                cursor.executescript(schema_sql)
                conn.commit()
            conn.close()
            logger.info("PostgreSQL database initialized successfully.")
            return
        except Exception as e:
            if settings.ENVIRONMENT == "production":
                raise RuntimeError(f"Failed to initialize PostgreSQL schema in production: {e}") from e
            logger.warning(f"Could not initialize PostgreSQL schema ({e}), falling back to SQLite initialization.")

    # SQLite schema initialization
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT,
        email TEXT,
        password_hash TEXT NOT NULL,
        salt TEXT DEFAULT '',
        display_name TEXT,
        is_admin BOOLEAN DEFAULT 0,
        is_email_verified BOOLEAN DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        display_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS recovery_codes (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code_hash TEXT NOT NULL,
        used_at TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        revoked_at TEXT
    );

    CREATE TABLE IF NOT EXISTS user_preferences (
        id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        default_profile TEXT DEFAULT 'family',
        default_priorities TEXT,
        distance_preferences TEXT,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS report_credits (
        id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        credits_remaining INTEGER DEFAULT 3,
        credits_used INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS search_history (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        locality_name TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        searched_at TEXT NOT NULL,
        provider TEXT
    );

    CREATE TABLE IF NOT EXISTS saved_locations (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        locality_name TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        label TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        locality_name TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        comparison_locality_name TEXT,
        comparison_lat REAL,
        comparison_lng REAL,
        user_profile TEXT,
        user_priorities TEXT,
        sections_included TEXT,
        verification_hash TEXT NOT NULL,
        pdf_storage_path TEXT,
        qr_code_url TEXT,
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'completed'
    );

    CREATE TABLE IF NOT EXISTS report_data_snapshots (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
        raw_evidence TEXT NOT NULL,
        aggregated_metrics TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        providers_used TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS report_properties (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
        property_address TEXT,
        floor_level TEXT,
        unit_facing TEXT,
        water_source_declared TEXT,
        power_backup_declared TEXT,
        rent_or_price TEXT,
        user_notes TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        razorpay_order_id TEXT UNIQUE NOT NULL,
        razorpay_payment_id TEXT UNIQUE,
        razorpay_signature TEXT,
        amount_paise INTEGER NOT NULL,
        amount_inr REAL NOT NULL,
        status TEXT NOT NULL,
        idempotency_key TEXT UNIQUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        report_id TEXT,
        locality_name TEXT,
        feedback_type TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS app_events (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        user_id TEXT,
        metadata TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Column migrations for existing tables if needed
    cursor.execute("PRAGMA table_info(users)")
    cols_dict = {col["name"]: dict(col) for col in cursor.fetchall()}
    existing_cols = set(cols_dict.keys())
    if "username" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "is_admin" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    if "updated_at" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")

    # If users table was created with email NOT NULL in an older schema, migrate to nullable
    if cols_dict.get("email", {}).get("notnull") == 1:
        cursor.execute("ALTER TABLE users RENAME TO users_old")
        cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT,
            email TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT DEFAULT '',
            display_name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            is_email_verified BOOLEAN DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        """)
        cursor.execute("""
        INSERT INTO users (id, username, email, password_hash, salt, display_name, is_admin, is_email_verified, created_at, updated_at)
        SELECT id, username, email, password_hash, salt, display_name, is_admin, is_email_verified, created_at, updated_at
        FROM users_old
        """)
        cursor.execute("DROP TABLE users_old")

    # Indexes
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower ON users (LOWER(username)) WHERE username IS NOT NULL")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recovery_codes_user ON recovery_codes (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (session_token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_order ON payments (razorpay_order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_events_type ON app_events (event_type)")

    conn.commit()
    conn.close()

# Initialize tables on import
init_db()
