import unittest
import os
import subprocess
import sys
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.db.local_db import (
    get_connection,
    get_database_mode,
    PostgresCursorWrapper,
    DB_PATH
)
from backend.app.db.repository import Repository

client = TestClient(app)

class TestDatabaseAndPersistence(unittest.TestCase):
    def setUp(self):
        self.orig_db_url = settings.DATABASE_URL
        self.orig_env = settings.ENVIRONMENT

    def tearDown(self):
        settings.DATABASE_URL = self.orig_db_url
        settings.ENVIRONMENT = self.orig_env

    def test_01_active_database_mode_and_data_integrity(self):
        """Verify active database mode is SQLite in local development and all records are preserved."""
        settings.DATABASE_URL = None
        self.assertEqual(get_database_mode(), "sqlite")
        self.assertTrue(os.path.exists(DB_PATH), f"SQLite database must exist at {DB_PATH}")

        conn = get_connection()
        cur = conn.cursor()

        # Verify core tables and record counts from existing production snapshot
        counts = {}
        for table in ["users", "profiles", "reports", "report_data_snapshots", "payments", "report_credits"]:
            cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
            counts[table] = cur.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(counts["users"], 430, "User accounts must be preserved")
        self.assertGreaterEqual(counts["reports"], 60, "Reports must be preserved")
        self.assertGreaterEqual(counts["payments"], 15, "Payment records must be preserved")
        self.assertGreaterEqual(counts["report_credits"], 430, "Report credits must be preserved")

    def test_02_postgres_query_translation_and_wrapper(self):
        """Verify PostgresCursorWrapper translates SQLite ? placeholders to PostgreSQL %s placeholders."""
        class MockPgCursor:
            def __init__(self):
                self.last_query = None
                self.last_params = None
                self.rowcount = 1

            def execute(self, query, params=None):
                self.last_query = query
                self.last_params = params

        mock_cur = MockPgCursor()
        wrapper = PostgresCursorWrapper(mock_cur)

        # 1. Query with multiple ? placeholders
        query = "SELECT * FROM users WHERE id = ? AND email = ? AND is_admin = ?"
        params = ("u123", "test@example.com", True)
        wrapper.execute(query, params)

        self.assertEqual(
            mock_cur.last_query,
            "SELECT * FROM users WHERE id = %s AND email = %s AND is_admin = %s",
            "Placeholders must be converted from ? to %s"
        )
        self.assertEqual(mock_cur.last_params, params)

        # 2. Query without params
        wrapper.execute("SELECT COUNT(*) FROM users")
        self.assertEqual(mock_cur.last_query, "SELECT COUNT(*) FROM users")
        self.assertIsNone(mock_cur.last_params)

    def test_03_production_database_fails_loudly_without_silent_fallback(self):
        """In production environment, an unreachable PostgreSQL database must fail loudly and raise RuntimeError."""
        settings.ENVIRONMENT = "production"
        # Point to a non-existent port on localhost to guarantee connection failure
        settings.DATABASE_URL = "postgresql://invalid_user:invalid_pass@127.0.0.1:59999/invalid_db"

        with self.assertRaises(RuntimeError) as ctx:
            get_connection()
        self.assertIn("Production database connection failed", str(ctx.exception))

    def test_04_ephemeral_filesystem_pdf_regeneration(self):
        """
        Verify that if a report PDF is missing on disk (ephemeral filesystem wipe),
        GET /api/reports/{id}/pdf automatically reconstitutes and regenerates the authentic PDF from the database snapshot.
        """
        settings.DATABASE_URL = None
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM reports ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row, "At least one report must exist in database")
        report_id = row["id"]

        # Simulate ephemeral filesystem wipe: delete PDF file from reports dir if it exists
        reports_dir = os.path.join(os.path.dirname(DB_PATH), "reports")
        pdf_file = os.path.join(reports_dir, f"report_{report_id}.pdf")
        if os.path.exists(pdf_file):
            os.remove(pdf_file)
        self.assertFalse(os.path.exists(pdf_file), "PDF file should be absent to simulate ephemeral wipe")

        # Call download endpoint
        resp = client.get(f"/api/reports/{report_id}/pdf")
        self.assertEqual(resp.status_code, 200, f"Expected 200 on PDF download, got {resp.status_code}")
        self.assertEqual(resp.headers.get("content-type"), "application/pdf")

        # Verify valid PDF header
        content = resp.content
        self.assertTrue(content.startswith(b"%PDF"), "Regenerated content must be a valid PDF starting with %PDF")
        self.assertTrue(os.path.exists(pdf_file), "Regenerated PDF file should now exist on disk")

    def test_05_migration_dry_run_script_execution(self):
        """Verify scripts/migrate_to_postgres.py --dry-run completes cleanly or aborts safely if target is already populated."""
        result = subprocess.run(
            [sys.executable, "scripts/migrate_to_postgres.py", "--dry-run"],
            capture_output=True,
            text=True
        )
        if "already populated" in result.stdout:
            self.assertEqual(result.returncode, 1, "Script must abort with exit code 1 when target is already populated")
            self.assertIn("Migration aborted for safety", result.stdout)
        else:
            self.assertEqual(result.returncode, 0, f"Dry-run should succeed with code 0: {result.stderr}")
            self.assertIn("DRY-RUN", result.stdout)
            self.assertIn("Table 'users':", result.stdout)
            self.assertIn("Table 'payments':", result.stdout)
            self.assertTrue(
                "Migration process completed successfully!" in result.stdout or "Preflight validation passed successfully" in result.stdout
            )


if __name__ == "__main__":
    unittest.main()
