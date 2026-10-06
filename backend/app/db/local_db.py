import sqlite3
import os
import json
import uuid
import hashlib
import hmac
from datetime import datetime
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "locallens_dev.db")

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if not salt:
        salt = uuid.uuid4().hex[:16]
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return key.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    key, _ = hash_password(password, salt)
    return hmac.compare_digest(key, password_hash)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        display_name TEXT,
        is_email_verified BOOLEAN DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        display_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
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
        credits_remaining INTEGER DEFAULT 0,
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
        status TEXT DEFAULT 'generating'
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

    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        report_id TEXT,
        locality_name TEXT,
        feedback_type TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

# Initialize tables on import
init_db()
