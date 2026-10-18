"""
LocalLens PostgreSQL Migration and Data Sync Utility.

Usage:
    python scripts/migrate_to_postgres.py [--dry-run] [--db-url DATABASE_URL]

Features:
- Validates PostgreSQL connection via DATABASE_URL
- Executes schema migration from backend/migrations/001_initial_schema.sql
- Detects already-populated target databases and aborts safely without overwriting
- Single atomic transaction for all data inserts and verification across all 14 tables
- No silent conflict suppression: ON CONFLICT DO NOTHING is removed so conflicts fail visibly
- Pre-commit verification: asserts PostgreSQL row counts equal SQLite source counts for all tables
- Full rollback on any insert failure or row count mismatch
- Supports --dry-run mode for preflight verification
- Never prints, logs, or echoes database secrets or passwords
"""

import os
import sys
import argparse
import sqlite3
import json
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL_PATH = PROJECT_ROOT / "backend" / "migrations" / "001_initial_schema.sql"
SQLITE_DB_PATH = PROJECT_ROOT / "backend" / "data" / "locallens_dev.db"

TABLE_ORDER = [
    "users", "profiles", "recovery_codes", "sessions", "user_preferences",
    "report_credits", "search_history", "saved_locations", "reports",
    "report_data_snapshots", "report_properties", "payments", "feedback", "app_events"
]

def mask_connection_string(url: str) -> str:
    """Mask credentials in a PostgreSQL connection string for safe logging."""
    if not url:
        return "<not-configured>"
    try:
        if "@" in url:
            prefix, rest = url.split("@", 1)
            scheme = prefix.split("://")[0] if "://" in prefix else "postgresql"
            return f"{scheme}://***:***@{rest}"
        return "postgresql://***:***"
    except Exception:
        return "postgresql://***:***"

def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Migrate LocalLens SQLite database to PostgreSQL / Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Perform preflight checks without executing schema changes or data writes")
    parser.add_argument("--db-url", type=str, default=None, help="PostgreSQL connection string (defaults to DATABASE_URL in .env)")
    return parser.parse_args(args)

def sanitize_row(table: str, cols: list, row_dict) -> tuple:
    """
    Sanitize SQLite row values for PostgreSQL strict typing and schema constraints.
    - Converts 0/1 integers to native Python booleans for PostgreSQL BOOLEAN columns.
    - If updated_at is NULL on records where created_at is present, safely falls back to
      created_at (matching the application's lifecycle semantics where an unmodified
      record has updated_at == created_at).
    """
    row_vals = []
    for c in cols:
        val = row_dict[c] if hasattr(row_dict, "__getitem__") else getattr(row_dict, c)
        if table == "users" and c in ("is_admin", "is_email_verified"):
            val = bool(val) if val is not None else False
        elif c == "updated_at" and val is None:
            # Semantic fallback: an un-updated record has updated_at == created_at
            created_at_val = row_dict["created_at"] if hasattr(row_dict, "__getitem__") else getattr(row_dict, "created_at", None)
            if created_at_val is not None:
                val = created_at_val
        row_vals.append(val)
    return tuple(row_vals)

def check_target_populated(cur_pg, table_order=TABLE_ORDER) -> list:
    """
    Check if any target tables in PostgreSQL already contain data.
    Returns a list of tuples: [(table_name, row_count), ...]
    """
    cur_pg.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    existing_pg_tables = {r[0] for r in cur_pg.fetchall()}

    populated_tables = []
    for t in table_order:
        if t in existing_pg_tables:
            cur_pg.execute(f'SELECT COUNT(*) FROM "{t}"')
            cnt = cur_pg.fetchone()[0]
            if cnt > 0:
                populated_tables.append((t, cnt))
    return populated_tables

def execute_schema_migration(cur_pg, schema_sql_path=MIGRATION_SQL_PATH):
    """Execute DDL statements from the migration SQL schema file."""
    if not schema_sql_path.exists():
        raise FileNotFoundError(f"Migration SQL file not found at {schema_sql_path}")
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cur_pg.execute(schema_sql)

def execute_data_migration(conn_sq, conn_pg, table_order=TABLE_ORDER):
    """
    Safely migrates SQLite data to PostgreSQL in a single atomic transaction.
    - Strict inserts: ON CONFLICT DO NOTHING is removed so conflicts fail visibly.
    - Pre-commit verification: asserts PostgreSQL row counts equal SQLite source counts for all tables.
    - If any error or count mismatch occurs, rolls back the entire transaction.
    """
    cur_sq = conn_sq.cursor()
    cur_pg = conn_pg.cursor()

    cur_sq.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row["name"] if isinstance(row, sqlite3.Row) else row[0] for row in cur_sq.fetchall()]

    ordered_tables = [t for t in table_order if t in tables] + [t for t in tables if t not in table_order]

    source_counts = {}
    table_data = {}

    # 1. Read all tables from SQLite
    for table in ordered_tables:
        cur_sq.execute(f'SELECT * FROM "{table}"')
        rows = cur_sq.fetchall()
        source_counts[table] = len(rows)
        table_data[table] = rows
        print(f"[DATA] Table '{table}': {len(rows)} records found in SQLite.")

    # 2. Begin single atomic transaction data migration
    print("\n[MIGRATE] Beginning atomic data transfer into PostgreSQL...")
    try:
        for table in ordered_tables:
            rows = table_data[table]
            if not rows:
                continue

            cols = rows[0].keys() if hasattr(rows[0], "keys") else [desc[0] for desc in cur_sq.description]
            col_names = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))

            # Strict INSERT without ON CONFLICT DO NOTHING so constraint violations fail visibly
            insert_query = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'

            data_to_insert = [sanitize_row(table, cols, row) for row in rows]
            cur_pg.executemany(insert_query, data_to_insert)
            print(f"  [DATA] Inserted {len(rows)} records into PostgreSQL '{table}' (uncommitted).")

        # 3. Post-transfer row count verification BEFORE commit
        print("\n[VERIFY] Verifying target PostgreSQL row counts against SQLite source...")
        for table in ordered_tables:
            expected = source_counts[table]
            cur_pg.execute(f'SELECT COUNT(*) FROM "{table}"')
            actual = cur_pg.fetchone()[0]
            print(f"  - Table '{table}': {actual} in PostgreSQL (expected {expected})")
            if actual != expected:
                raise ValueError(
                    f"Row count mismatch in table '{table}': PostgreSQL has {actual}, expected {expected}"
                )

        print("[OK] All table row counts match source SQLite exactly.")
        conn_pg.commit()
        print("[SUCCESS] Data migration committed successfully as a single atomic transaction!")
        return source_counts

    except Exception as e:
        conn_pg.rollback()
        print(f"\n[ROLLBACK] Migration failed: {e}. All changes rolled back cleanly.")
        raise

def run_migration(cli_args=None):
    args = parse_args(cli_args)

    # Load .env if present
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ and val:
                        os.environ[key] = val

    db_url = args.db_url or os.getenv("DATABASE_URL")
    print("=" * 60)
    print("LocalLens Database Migration: SQLite -> PostgreSQL")
    print("=" * 60)
    print(f"Dry Run: {args.dry_run}")
    print(f"Target Database: {mask_connection_string(db_url)}")
    print(f"SQLite Source: {SQLITE_DB_PATH} (exists: {SQLITE_DB_PATH.exists()})")
    print(f"Migration Schema: {MIGRATION_SQL_PATH} (exists: {MIGRATION_SQL_PATH.exists()})")
    print("-" * 60)

    # Check if DATABASE_URL is available
    if not db_url:
        print("\n[INFO] No DATABASE_URL configured. LocalLens is operating in local SQLite persistence mode.")
        if args.dry_run:
            print("[DRY-RUN] Inspecting SQLite source database and migration schema...")
            if not MIGRATION_SQL_PATH.exists():
                print(f"[ERROR] Migration SQL file not found at {MIGRATION_SQL_PATH}")
                return 1
            with open(MIGRATION_SQL_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
            print(f"[DRY-RUN] Schema defines {len(statements)} DDL statements in {MIGRATION_SQL_PATH.name}.")

            if SQLITE_DB_PATH.exists():
                conn_sq = sqlite3.connect(SQLITE_DB_PATH)
                conn_sq.row_factory = sqlite3.Row
                cur_sq = conn_sq.cursor()
                cur_sq.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = [row["name"] for row in cur_sq.fetchall()]
                ordered_tables = [t for t in TABLE_ORDER if t in tables] + [t for t in tables if t not in TABLE_ORDER]
                total_records = 0
                for table in ordered_tables:
                    cur_sq.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                    count = cur_sq.fetchone()[0]
                    total_records += count
                    print(f"  [DRY-RUN] Table '{table}': {count} records ready for migration.")
                conn_sq.close()
                print(f"[DRY-RUN] Total: {total_records} records across {len(ordered_tables)} tables.")
            print("[DRY-RUN] Preflight validation passed successfully. Set DATABASE_URL to execute migration.")
            return 0
        else:
            print("To migrate to PostgreSQL / Supabase, set DATABASE_URL in .env or pass --db-url.")
            return 0

    # Test psycopg2 import
    try:
        import psycopg2
    except ImportError:
        print("\n[ERROR] Python package 'psycopg2' is not installed in the current environment.")
        print("Install it with: pip install psycopg2-binary")
        return 1

    # Check connection
    try:
        conn_pg = psycopg2.connect(db_url)
        conn_pg.autocommit = False
        print("[OK] Successfully connected to PostgreSQL target.")
    except Exception as e:
        print(f"\n[ERROR] Could not connect to PostgreSQL target: {e}")
        return 1

    try:
        cur_pg = conn_pg.cursor()

        # Step 1: Pre-migration check for already-populated target database
        populated = check_target_populated(cur_pg, TABLE_ORDER)
        if populated:
            print("\n[ABORT] Target PostgreSQL database is already populated! Migration aborted for safety.")
            for t, cnt in populated:
                print(f"  - Table '{t}' already contains {cnt} records.")
            print("To prevent accidental overwrites or duplicate errors, the migration utility will not run against a populated database.")
            print("If you intend to re-migrate, you must explicitly clean or truncate the target tables manually.")
            return 1

        # Step 2: Schema Migration
        if not MIGRATION_SQL_PATH.exists():
            print(f"[ERROR] Migration SQL file not found at {MIGRATION_SQL_PATH}")
            return 1

        if args.dry_run:
            print("[DRY-RUN] Would apply migration SQL schema statements:")
            with open(MIGRATION_SQL_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            for stmt in schema_sql.split(";"):
                clean = stmt.strip()
                if clean:
                    first_line = clean.split("\n")[0][:60]
                    print(f"  - {first_line}...")
        else:
            print("[APPLY] Executing schema migration...")
            execute_schema_migration(cur_pg, MIGRATION_SQL_PATH)
            conn_pg.commit()
            print("[OK] Schema migration applied successfully.")

        # Step 3: Migrate data from SQLite in a single atomic transaction
        if SQLITE_DB_PATH.exists():
            conn_sq = sqlite3.connect(SQLITE_DB_PATH)
            conn_sq.row_factory = sqlite3.Row
            cur_sq = conn_sq.cursor()

            cur_sq.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row["name"] for row in cur_sq.fetchall()]
            ordered_tables = [t for t in TABLE_ORDER if t in tables] + [t for t in tables if t not in TABLE_ORDER]

            if args.dry_run:
                total_dry = 0
                for table in ordered_tables:
                    cur_sq.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                    count = cur_sq.fetchone()[0]
                    total_dry += count
                    print(f"[DATA] Table '{table}': {count} records found in SQLite.")
                    if count > 0:
                        print(f"  [DRY-RUN] Would transfer {count} records into PostgreSQL '{table}'.")
                print(f"[DRY-RUN] Total: {total_dry} records across {len(ordered_tables)} tables would be transferred in a single atomic transaction.")
                print("[DRY-RUN] Verification step would assert all PostgreSQL table counts match source counts prior to commit.")
            else:
                execute_data_migration(conn_sq, conn_pg, ordered_tables)

            conn_sq.close()
        else:
            print("[INFO] No SQLite database found to migrate data from.")

        print("\n" + "=" * 60)
        print("Migration process completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        conn_pg.rollback()
        print(f"\n[FATAL] Migration failed with error: {e}")
        return 1
    finally:
        conn_pg.close()

if __name__ == "__main__":
    sys.exit(run_migration())
