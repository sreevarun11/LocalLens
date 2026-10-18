"""
Automated unit tests for SQLite-to-PostgreSQL migration safety guarantees.

Verifies:
1. Single atomic transaction: rollback on any error (no partial table commits).
2. Visible conflict failure: no silent skipping via ON CONFLICT DO NOTHING.
3. Row count verification: count mismatches between source and target trigger rollback.
4. Populated target protection: aborts immediately without modifying or overwriting data.
5. Successful end-to-end migration with single atomic commit and count matching.
6. Boolean sanitization for strict PostgreSQL BOOLEAN columns.
7. Empty public schema behavior: initially empty schema passes pre-checks and applies cleanly.
8. Partially created schema detection: detects pre-existing populated tables safely.
9. Empty table handling: verifies that tables with 0 rows (like app_events) are validated accurately.
10. Refusal to overwrite: refuses to overwrite, truncate, or reuse pre-existing data.
11. NULL updated_at resolution: falls back to created_at matching application lifecycle semantics.
12. Genuinely invalid rows: rolls back transaction if both timestamps or required fields are missing.
13. Production SQLite dataset verification: asserts all 457 users sanitize without null constraint violations.

Note: Isolated tests only. Does not connect to or alter any live Supabase database.
"""

import unittest
import sqlite3
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.migrate_to_postgres import (
    TABLE_ORDER,
    SQLITE_DB_PATH,
    sanitize_row,
    check_target_populated,
    execute_data_migration,
    run_migration
)

class MockPgCursor:
    def __init__(self, target_counts=None, existing_tables=None, fail_on_table=None, fail_with_exception=None, simulate_conflict=False):
        self.executed_statements = []
        self.executed_many = []
        self.target_counts = target_counts if target_counts is not None else {}
        self.existing_tables = set(existing_tables) if existing_tables is not None else set()
        self.fail_on_table = fail_on_table
        self.fail_with_exception = fail_with_exception or RuntimeError
        self.simulate_conflict = simulate_conflict
        self._result = []

    def execute(self, query, params=None):
        self.executed_statements.append((query, params))
        if "information_schema.tables" in query:
            self._result = [(t,) for t in self.existing_tables]
        elif query.strip().startswith("SELECT COUNT(*) FROM"):
            m = re.search(r'SELECT COUNT\(\*\) FROM "(\w+)"', query)
            if m:
                tbl = m.group(1)
                cnt = self.target_counts.get(tbl, 0)
                self._result = [(cnt,)]
            else:
                self._result = [(0,)]
        else:
            self._result = []

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result[0] if self._result else None

    def executemany(self, query, params_seq):
        self.executed_many.append((query, params_seq))
        m = re.search(r'INSERT INTO "(\w+)"', query)
        tbl = m.group(1) if m else "unknown"

        # Check for ON CONFLICT DO NOTHING (it MUST NOT be present)
        if "ON CONFLICT" in query:
            raise AssertionError(f"Query contains ON CONFLICT: {query}. It must fail visibly!")

        # Enforce PostgreSQL NOT NULL constraints
        if tbl == "users":
            m_cols = re.search(r'INSERT INTO "users" \((.*?)\)', query)
            if m_cols:
                cols = [c.strip().strip('"') for c in m_cols.group(1).split(",")]
                updated_at_idx = cols.index("updated_at") if "updated_at" in cols else -1
                created_at_idx = cols.index("created_at") if "created_at" in cols else -1
                for row in params_seq:
                    if updated_at_idx >= 0 and row[updated_at_idx] is None:
                        raise sqlite3.IntegrityError('null value in column "updated_at" of relation "users" violates not-null constraint')
                    if created_at_idx >= 0 and row[created_at_idx] is None:
                        raise sqlite3.IntegrityError('null value in column "created_at" of relation "users" violates not-null constraint')

        if self.simulate_conflict and tbl == "users":
            raise sqlite3.IntegrityError("duplicate key value violates unique constraint 'idx_users_username_lower'")

        if self.fail_on_table and tbl == self.fail_on_table:
            raise self.fail_with_exception(f"Simulated failure on table {tbl}")

        # Record inserted count
        self.target_counts[tbl] = self.target_counts.get(tbl, 0) + len(params_seq)

class MockPgConnection:
    def __init__(self, target_counts=None, existing_tables=None, fail_on_table=None, fail_with_exception=None, simulate_conflict=False):
        self.autocommit = False
        self.committed = False
        self.rolled_back = False
        self.commit_count = 0
        self.rollback_count = 0
        self.cursor_obj = MockPgCursor(target_counts, existing_tables, fail_on_table, fail_with_exception, simulate_conflict)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True
        self.commit_count += 1

    def rollback(self):
        self.rolled_back = True
        self.rollback_count += 1

    def close(self):
        pass


class MigrationSafetyTests(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite source database with mock schema and sample data
        self.conn_sq = sqlite3.connect(":memory:")
        self.conn_sq.row_factory = sqlite3.Row
        cur = self.conn_sq.cursor()

        cur.execute("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT,
                password_hash TEXT,
                salt TEXT,
                display_name TEXT,
                is_admin INTEGER,
                is_email_verified INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE profiles (
                id TEXT PRIMARY KEY,
                display_name TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE reports (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                locality_name TEXT,
                lat REAL,
                lng REAL,
                verification_hash TEXT,
                pdf_storage_path TEXT,
                created_at TEXT,
                status TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE app_events (
                id TEXT PRIMARY KEY,
                event_type TEXT,
                user_id TEXT,
                metadata TEXT,
                created_at TEXT
            )
        """)

        # Insert test records: u1 has updated_at = NULL (simulating the 281 production users)
        cur.execute("""
            INSERT INTO users VALUES
            ('u1', 'alice', 'alice@test.com', 'hash1', 'salt1', 'Alice', 0, 1, '2026-10-18T10:00:00', NULL),
            ('u2', 'bob', 'bob@test.com', 'hash2', 'salt2', 'Bob', 1, 1, '2026-10-18T10:00:00', '2026-10-18T11:00:00')
        """)
        cur.execute("""
            INSERT INTO profiles VALUES
            ('u1', 'Alice', '2026-10-18T10:00:00', '2026-10-18T10:00:00'),
            ('u2', 'Bob', '2026-10-18T10:00:00', '2026-10-18T10:00:00')
        """)
        cur.execute("""
            INSERT INTO reports VALUES
            ('r1', 'u1', 'Audit Report', 'Gachibowli', 17.44, 78.34, 'vhash1', 'path1', '2026-10-18T10:00:00', 'completed')
        """)
        self.conn_sq.commit()

        self.test_tables = ["users", "profiles", "reports", "app_events"]

    def tearDown(self):
        self.conn_sq.close()

    def test_single_atomic_transaction_success(self):
        """Test successful migration: commits exactly once after all tables verify, including NULL updated_at fallback."""
        mock_pg = MockPgConnection()
        source_counts = execute_data_migration(self.conn_sq, mock_pg, self.test_tables)

        self.assertEqual(source_counts["users"], 2)
        self.assertEqual(source_counts["profiles"], 2)
        self.assertEqual(source_counts["reports"], 1)
        self.assertEqual(source_counts["app_events"], 0)

        # Verified single commit at end
        self.assertTrue(mock_pg.committed)
        self.assertEqual(mock_pg.commit_count, 1)
        self.assertFalse(mock_pg.rolled_back)
        self.assertEqual(mock_pg.rollback_count, 0)

        # Verified all rows recorded in target
        self.assertEqual(mock_pg.cursor_obj.target_counts["users"], 2)
        self.assertEqual(mock_pg.cursor_obj.target_counts["profiles"], 2)
        self.assertEqual(mock_pg.cursor_obj.target_counts["reports"], 1)
        self.assertEqual(mock_pg.cursor_obj.target_counts.get("app_events", 0), 0)

    def test_single_atomic_transaction_rollback_on_failure(self):
        """Test atomic rollback: failure on child table aborts and rolls back everything without committing."""
        mock_pg = MockPgConnection(fail_on_table="reports")

        with self.assertRaises(RuntimeError) as ctx:
            execute_data_migration(self.conn_sq, mock_pg, self.test_tables)

        self.assertIn("Simulated failure on table reports", str(ctx.exception))
        self.assertFalse(mock_pg.committed, "Target must NOT be committed if any table fails")
        self.assertEqual(mock_pg.commit_count, 0)
        self.assertTrue(mock_pg.rolled_back, "Target must execute rollback on failure")
        self.assertEqual(mock_pg.rollback_count, 1)

    def test_conflict_detection_fails_visibly(self):
        """Test that ON CONFLICT DO NOTHING is absent and unique conflicts fail visibly and trigger rollback."""
        mock_pg = MockPgConnection(simulate_conflict=True)

        with self.assertRaises(sqlite3.IntegrityError) as ctx:
            execute_data_migration(self.conn_sq, mock_pg, self.test_tables)

        self.assertIn("violates unique constraint", str(ctx.exception))
        self.assertFalse(mock_pg.committed)
        self.assertTrue(mock_pg.rolled_back)
        self.assertEqual(mock_pg.rollback_count, 1)

    def test_count_mismatch_detection_triggers_rollback(self):
        """Test that post-transfer count mismatch raises ValueError and rolls back before commit."""
        mock_pg = MockPgConnection(target_counts={"users": 1, "profiles": 2, "reports": 1, "app_events": 0})
        original_executemany = mock_pg.cursor_obj.executemany
        def altered_executemany(q, params):
            if "users" in q:
                mock_pg.cursor_obj.target_counts["users"] = 1 # Force mismatch (expected 2)
            else:
                original_executemany(q, params)
        mock_pg.cursor_obj.executemany = altered_executemany

        with self.assertRaises(ValueError) as ctx:
            execute_data_migration(self.conn_sq, mock_pg, self.test_tables)

        self.assertIn("Row count mismatch in table 'users'", str(ctx.exception))
        self.assertFalse(mock_pg.committed)
        self.assertTrue(mock_pg.rolled_back)
        self.assertEqual(mock_pg.rollback_count, 1)

    def test_empty_app_events_table_handling(self):
        """Test that initially empty table (app_events with 0 rows) verifies count 0 == 0 cleanly."""
        mock_pg = MockPgConnection()
        source_counts = execute_data_migration(self.conn_sq, mock_pg, ["app_events"])
        self.assertEqual(source_counts["app_events"], 0)
        self.assertTrue(mock_pg.committed)
        self.assertEqual(mock_pg.commit_count, 1)

    def test_initially_empty_public_schema_proceeds(self):
        """Test that an initially empty public schema (0 tables) passes pre-checks without false aborts."""
        mock_cur = MockPgCursor(existing_tables=[])
        populated = check_target_populated(mock_cur, TABLE_ORDER)
        self.assertEqual(populated, [])

    def test_partially_created_schema_detection(self):
        """Test that a partially created schema from an earlier attempt is detected safely."""
        # Scenario A: Tables exist from failed DDL/rollback but are empty -> safe to proceed with idempotent DDL
        mock_cur_empty = MockPgCursor(existing_tables=["users", "profiles"], target_counts={"users": 0, "profiles": 0})
        self.assertEqual(check_target_populated(mock_cur_empty, TABLE_ORDER), [])

        # Scenario B: Partial tables exist with rows -> must abort immediately
        mock_cur_partial = MockPgCursor(existing_tables=["users", "profiles"], target_counts={"users": 10, "profiles": 0})
        populated = check_target_populated(mock_cur_partial, TABLE_ORDER)
        self.assertEqual(len(populated), 1)
        self.assertEqual(populated[0], ("users", 10))

    def test_refusal_to_overwrite_or_reuse_existing_data(self):
        """Test that run_migration strictly refuses to execute if target contains any rows."""
        mock_conn = MockPgConnection(
            existing_tables=["users", "profiles"],
            target_counts={"users": 100, "profiles": 100}
        )
        with patch("psycopg2.connect", return_value=mock_conn):
            exit_code = run_migration(["--db-url", "postgresql://test:test@localhost:5432/test"])
            self.assertEqual(exit_code, 1, "Must refuse to execute and return code 1")
            self.assertFalse(mock_conn.committed, "Must never commit writes to populated target")

    def test_sanitize_row_boolean_handling(self):
        """Test boolean conversion for PostgreSQL strict BOOLEAN type."""
        cols = ["id", "username", "is_admin", "is_email_verified"]
        row_admin = {"id": "1", "username": "admin", "is_admin": 1, "is_email_verified": 1}
        row_user = {"id": "2", "username": "user", "is_admin": 0, "is_email_verified": 0}
        row_none = {"id": "3", "username": "anon", "is_admin": None, "is_email_verified": None}

        res_admin = sanitize_row("users", cols, row_admin)
        res_user = sanitize_row("users", cols, row_user)
        res_none = sanitize_row("users", cols, row_none)

        self.assertEqual(res_admin, ("1", "admin", True, True))
        self.assertEqual(res_user, ("2", "user", False, False))
        self.assertEqual(res_none, ("3", "anon", False, False))
        self.assertIsInstance(res_admin[2], bool)
        self.assertIsInstance(res_user[2], bool)

    def test_sanitize_row_updated_at_fallback_to_created_at(self):
        """Test that NULL updated_at falls back to created_at, matching application lifecycle semantics."""
        cols = ["id", "username", "created_at", "updated_at"]
        row_null_updated = {"id": "u1", "username": "alice", "created_at": "2026-09-30T16:41:43.888904", "updated_at": None}
        row_with_updated = {"id": "u2", "username": "bob", "created_at": "2026-09-30T16:41:43.888904", "updated_at": "2026-10-16T12:00:00"}

        res_fallback = sanitize_row("users", cols, row_null_updated)
        res_preserved = sanitize_row("users", cols, row_with_updated)

        self.assertEqual(res_fallback[3], "2026-09-30T16:41:43.888904", "NULL updated_at must fall back to created_at")
        self.assertEqual(res_preserved[3], "2026-10-16T12:00:00", "Existing updated_at must be preserved unchanged")

    def test_genuinely_invalid_row_with_both_timestamps_null_triggers_rollback(self):
        """Test that a genuinely corrupted row (both created_at and updated_at NULL) fails visibly and rolls back."""
        cur = self.conn_sq.cursor()
        cur.execute("INSERT INTO users VALUES ('bad_user', 'bad', 'bad@test.com', 'h', 's', 'Bad', 0, 1, NULL, NULL)")
        self.conn_sq.commit()

        mock_pg = MockPgConnection()
        with self.assertRaises(sqlite3.IntegrityError) as ctx:
            execute_data_migration(self.conn_sq, mock_pg, ["users"])

        self.assertIn("violates not-null constraint", str(ctx.exception))
        self.assertFalse(mock_pg.committed)
        self.assertTrue(mock_pg.rolled_back)
        self.assertEqual(mock_pg.rollback_count, 1)

    def test_production_sqlite_source_users_sanitization(self):
        """Verify that all 457 production SQLite users sanitize with zero NULL updated_at values."""
        if not SQLITE_DB_PATH.exists():
            self.skipTest("Production SQLite database not found")

        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 457, "Production users count must be 457")
        cols = rows[0].keys()
        updated_at_idx = cols.index("updated_at")
        created_at_idx = cols.index("created_at")

        null_before = sum(1 for r in rows if r["updated_at"] is None)
        self.assertEqual(null_before, 281, "Exactly 281 rows in SQLite have NULL updated_at")

        sanitized_rows = [sanitize_row("users", cols, r) for r in rows]
        null_after = sum(1 for r in sanitized_rows if r[updated_at_idx] is None)
        self.assertEqual(null_after, 0, "After sanitization, 0 rows must have NULL updated_at")

        # Verify that for the 281 rows, updated_at == created_at
        for orig, sanitized in zip(rows, sanitized_rows):
            if orig["updated_at"] is None:
                self.assertEqual(sanitized[updated_at_idx], sanitized[created_at_idx])
            else:
                self.assertEqual(sanitized[updated_at_idx], orig["updated_at"])

if __name__ == "__main__":
    unittest.main()
