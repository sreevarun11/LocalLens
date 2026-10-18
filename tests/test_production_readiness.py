import unittest
import uuid
import hmac
import hashlib
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token
from backend.app.api.reports import _regenerate_pdf_from_snapshot

client = TestClient(app)

class TestProductionReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test users
        cls.user_a_name = f"user_a_{uuid.uuid4().hex[:8]}"
        cls.user_a = Repository.create_user(
            username=cls.user_a_name,
            password="StrongPassword123!",
            display_name="User Alpha",
            email=f"{cls.user_a_name}@example.com",
            is_admin=False,
            is_email_verified=True
        )
        cls.token_a = create_access_token(
            user_id=cls.user_a["id"],
            username_or_email=cls.user_a_name,
            is_email_verified=True,
            is_admin=False
        )

        cls.user_b_name = f"user_b_{uuid.uuid4().hex[:8]}"
        cls.user_b = Repository.create_user(
            username=cls.user_b_name,
            password="StrongPassword123!",
            display_name="User Beta",
            email=f"{cls.user_b_name}@example.com",
            is_admin=False,
            is_email_verified=True
        )
        cls.token_b = create_access_token(
            user_id=cls.user_b["id"],
            username_or_email=cls.user_b_name,
            is_email_verified=True,
            is_admin=False
        )

    def test_01_jwt_secret_enforcement_in_production(self):
        """Production must fail loudly if SUPABASE_JWT_SECRET is missing, short, or legacy default."""
        with patch.object(settings, "ENVIRONMENT", "production"):
            # Missing / None
            with patch.object(settings, "SUPABASE_JWT_SECRET", None):
                with self.assertRaises(RuntimeError) as ctx:
                    settings.get_jwt_secret()
                self.assertIn("SUPABASE_JWT_SECRET", str(ctx.exception))

            # Too short (< 32 chars)
            with patch.object(settings, "SUPABASE_JWT_SECRET", "short_secret_key"):
                with self.assertRaises(RuntimeError) as ctx:
                    settings.get_jwt_secret()
                self.assertIn("at least 32 characters", str(ctx.exception))

            # Legacy insecure default
            with patch.object(settings, "SUPABASE_JWT_SECRET", "locallens_super_secure_secret_key_4.0"):
                with self.assertRaises(RuntimeError) as ctx:
                    settings.get_jwt_secret()
                self.assertIn("SUPABASE_JWT_SECRET", str(ctx.exception))

            # Valid production key
            valid_secret = "a" * 32
            with patch.object(settings, "SUPABASE_JWT_SECRET", valid_secret):
                self.assertEqual(settings.get_jwt_secret(), valid_secret)

    def test_02_cors_origins_enforcement_in_production(self):
        """Production CORS must require explicit non-localhost domains and reject empty origins."""
        with patch.object(settings, "ENVIRONMENT", "production"):
            with patch.object(settings, "CORS_ORIGINS", ""):
                with patch.object(settings, "PUBLIC_BASE_URL", None):
                    with self.assertRaises(ValueError):
                        settings.get_cors_origins()

            # Configured origins
            with patch.object(settings, "CORS_ORIGINS", "https://locallens.vercel.app, https://app.locallens.in"):
                with patch.object(settings, "PUBLIC_BASE_URL", "https://locallens.vercel.app"):
                    origins = settings.get_cors_origins()
                    self.assertIn("https://locallens.vercel.app", origins)
                    self.assertIn("https://app.locallens.in", origins)
                    self.assertNotIn("*", origins)
                    self.assertFalse(any("localhost" in o for o in origins))

    def test_03_admin_provisioning_in_production_fails_without_password(self):
        """In production, auto-provisioning an uncreated admin without ADMIN_PASSWORD must raise RuntimeError."""
        uncreated_admin = f"new_admin_{uuid.uuid4().hex[:8]}"
        with patch.object(settings, "ENVIRONMENT", "production"):
            with self.assertRaises(RuntimeError) as ctx:
                Repository.provision_admin_user(uncreated_admin, password=None)
            self.assertIn("ADMIN_PASSWORD environment variable", str(ctx.exception))

    def test_04_payment_order_fails_closed_in_production_when_unconfigured(self):
        """In production, creating a payment order without Razorpay keys must fail with HTTP 503."""
        # Set user credits to 0 so order creation is triggered
        from backend.app.db.local_db import get_connection
        c = get_connection()
        cur = c.cursor()
        cur.execute("UPDATE report_credits SET credits_remaining = 0 WHERE user_id = ?", (self.user_a["id"],))
        c.commit()
        c.close()

        prod_secret = "s" * 32
        with patch.object(settings, "ENVIRONMENT", "production"):
            with patch.object(settings, "SUPABASE_JWT_SECRET", prod_secret):
                token = create_access_token(user_id=self.user_a["id"], username_or_email=self.user_a_name)
                headers = {"Authorization": f"Bearer {token}"}
                with patch.object(settings, "RAZORPAY_KEY_ID", None):
                    with patch.object(settings, "RAZORPAY_KEY_SECRET", None):
                        resp = client.post("/api/payments/create-order", json={}, headers=headers)
                        self.assertEqual(resp.status_code, 503)
                        self.assertIn("unavailable in production", resp.json()["error"]["message"])

    def test_05_payment_verification_fails_closed_in_production_without_secret(self):
        """In production, verifying a payment without RAZORPAY_KEY_SECRET must return HTTP 503."""
        prod_secret = "s" * 32
        with patch.object(settings, "ENVIRONMENT", "production"):
            with patch.object(settings, "SUPABASE_JWT_SECRET", prod_secret):
                token = create_access_token(user_id=self.user_a["id"], username_or_email=self.user_a_name)
                headers = {"Authorization": f"Bearer {token}"}
                payload = {
                    "razorpay_order_id": "order_test_123",
                    "razorpay_payment_id": "pay_test_123",
                    "razorpay_signature": "sig_test_123"
                }
                with patch.object(settings, "RAZORPAY_KEY_SECRET", None):
                    resp = client.post("/api/payments/verify-payment", json=payload, headers=headers)
                    self.assertEqual(resp.status_code, 503)
                    self.assertIn("secret is not configured", resp.json()["error"]["message"])

    def test_06_payment_verification_atomic_idempotency_and_single_credit(self):
        """Payment completion must be idempotent and grant exactly 1 credit across multiple verifications."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        secret = "test_razorpay_secret_key_123"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"

        # Record order for user_a
        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            initial_credits = Repository.get_credits(self.user_a["id"])["credits_remaining"]

            # First verification
            resp1 = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp1.status_code, 200)
            self.assertTrue(resp1.json()["success"])
            credits_after_first = Repository.get_credits(self.user_a["id"])["credits_remaining"]
            self.assertEqual(credits_after_first, initial_credits + 1)

            # Duplicate verification (replay attempt)
            resp2 = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp2.status_code, 200)
            self.assertTrue(resp2.json()["success"])
            credits_after_second = Repository.get_credits(self.user_a["id"])["credits_remaining"]
            self.assertEqual(credits_after_second, initial_credits + 1, "Credits must NOT increment on replay")

    def test_07_payment_verification_ownership_validation(self):
        """User B must not be able to verify/claim User A's order."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        secret = "test_razorpay_secret_key_123"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"

        # Record order owned by user_a
        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        # User B attempts to claim it
        headers_b = {"Authorization": f"Bearer {self.token_b}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            resp = client.post("/api/payments/verify-payment", json=payload, headers=headers_b)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("could not be processed", resp.json()["error"]["message"])

    def test_08_verify_email_simulate_forbidden_in_production(self):
        """In production, /api/auth/verify-email-simulate must return 403 Forbidden."""
        prod_secret = "s" * 32
        with patch.object(settings, "ENVIRONMENT", "production"):
            with patch.object(settings, "SUPABASE_JWT_SECRET", prod_secret):
                token = create_access_token(user_id=self.user_a["id"], username_or_email=self.user_a_name)
                headers = {"Authorization": f"Bearer {token}"}
                resp = client.post("/api/auth/verify-email-simulate", headers=headers)
                self.assertEqual(resp.status_code, 403)
                self.assertIn("disabled in production", resp.json()["error"]["message"])

    def test_09_regenerate_pdf_rewrites_stale_localhost_url(self):
        """Stale localhost QR URLs must be rewritten with public_base_url."""
        dummy_report_id = str(uuid.uuid4())
        mock_report = {
            "id": dummy_report_id,
            "qr_code_url": f"http://localhost:5173/verify/{dummy_report_id}",
            "locality_name": "Kondapur",
            "lat": 17.46,
            "lng": 78.35,
            "verification_hash": "hash_xyz",
            "snapshot": {"raw_evidence": []}
        }

        with patch.object(settings, "PUBLIC_BASE_URL", "https://locallens.vercel.app"):
            with patch("backend.app.api.reports.generate_report_pdf") as mock_pdf:
                _regenerate_pdf_from_snapshot(mock_report, dummy_report_id)
                self.assertTrue(mock_pdf.called)
                _, kwargs = mock_pdf.call_args
                self.assertEqual(
                    kwargs["verification_url"],
                    f"https://locallens.vercel.app/verify/{dummy_report_id}"
                )

if __name__ == "__main__":
    unittest.main()
