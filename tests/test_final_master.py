import unittest
import uuid
import hmac
import hashlib
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.db.local_db import get_connection, verify_password
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token
from backend.app.auth.argon2_utils import generate_recovery_codes, verify_recovery_code

client = TestClient(app)

class TestFinalMasterFullSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an admin user directly
        cls.admin_username = f"admin_{uuid.uuid4().hex[:6]}"
        cls.admin_email = f"{cls.admin_username}@locallens.app"
        cls.admin_password = "AdminSuperSecurePassword2026!"
        cls.admin_user = Repository.create_user(
            username=cls.admin_username,
            password=cls.admin_password,
            display_name="Master Administrator",
            email=cls.admin_email,
            is_admin=True,
            is_email_verified=True
        )
        cls.admin_token = create_access_token(
            user_id=cls.admin_user["id"],
            username_or_email=cls.admin_username,
            is_email_verified=True,
            is_admin=True
        )

    def test_01_user_registration_argon2_and_recovery_codes(self):
        """Test username/password registration with Argon2id and 10 single-use recovery codes."""
        test_uname = f"u_{uuid.uuid4().hex[:8]}"
        test_pwd = "MasterTestPassword123!"

        # 1. Password shorter than 10 characters must be rejected
        short_resp = client.post("/api/auth/register", json={
            "username": test_uname,
            "password": "short"
        })
        self.assertIn(short_resp.status_code, [400, 422])

        # 2. Valid registration
        reg_resp = client.post("/api/auth/register", json={
            "username": test_uname,
            "display_name": "Test Citizen",
            "email": f"{test_uname}@example.com",
            "password": test_pwd
        })
        self.assertEqual(reg_resp.status_code, 200)
        data = reg_resp.json()
        self.assertIn("access_token", data)
        self.assertIn("recovery_codes", data)
        recovery_codes = data["recovery_codes"]
        self.assertEqual(len(recovery_codes), 10)
        self.assertTrue(all(c.startswith("LL-") for c in recovery_codes))

        user = data["user"]
        self.assertEqual(user["username"], test_uname)

        # 3. Verify in DB that password and recovery codes are hashed (Argon2id)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],))
        pwd_hash = cursor.fetchone()["password_hash"]
        self.assertTrue(pwd_hash.startswith("$argon2id$") or pwd_hash.startswith("$argon2"))

        cursor.execute("SELECT code_hash, used_at FROM recovery_codes WHERE user_id = ?", (user["id"],))
        codes_in_db = cursor.fetchall()
        self.assertEqual(len(codes_in_db), 10)
        for row in codes_in_db:
            self.assertIsNone(row["used_at"])
            # Codes must be hashed, never stored plaintext
            self.assertFalse(row["code_hash"].startswith("LL-"))
            self.assertTrue(row["code_hash"].startswith("$argon2id$") or row["code_hash"].startswith("$argon2"))
        conn.close()

        # 4. Login with username (case-insensitive)
        login_resp = client.post("/api/auth/login", json={
            "username": test_uname.upper(),
            "password": test_pwd
        })
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

        # 5. Login with email
        login_email_resp = client.post("/api/auth/login", json={
            "email": f"{test_uname}@example.com",
            "password": test_pwd
        })
        self.assertEqual(login_email_resp.status_code, 200)

        # 6. Bad password -> 401
        bad_pwd_resp = client.post("/api/auth/login", json={
            "username": test_uname,
            "password": "WrongPassword123!"
        })
        self.assertEqual(bad_pwd_resp.status_code, 401)

    def test_02_password_recovery_with_single_use_code_and_session_revocation(self):
        """Test account password recovery using single-use recovery code and session revocation."""
        uname = f"rec_{uuid.uuid4().hex[:8]}"
        initial_pwd = "InitialPassword123!"
        new_pwd = "BrandNewSecurePassword456!"

        # Register user
        reg_resp = client.post("/api/auth/register", json={
            "username": uname,
            "password": initial_pwd
        })
        self.assertEqual(reg_resp.status_code, 200)
        reg_data = reg_resp.json()
        initial_token = reg_data["access_token"]
        recovery_codes = reg_data["recovery_codes"]
        code_to_use = recovery_codes[0]

        # Verify initial session is valid
        self.assertTrue(Repository.is_session_valid(initial_token))

        # Perform password recovery with recovery code
        rec_resp = client.post("/api/auth/recover-password", json={
            "username": uname,
            "recovery_code": code_to_use,
            "new_password": new_pwd
        })
        self.assertEqual(rec_resp.status_code, 200)

        # 1. Sessions must be revoked
        self.assertFalse(Repository.is_session_valid(initial_token))

        # 2. Old password cannot login
        old_login = client.post("/api/auth/login", json={
            "username": uname,
            "password": initial_pwd
        })
        self.assertEqual(old_login.status_code, 401)

        # 3. New password logs in successfully
        new_login = client.post("/api/auth/login", json={
            "username": uname,
            "password": new_pwd
        })
        self.assertEqual(new_login.status_code, 200)

        # 4. Attempting to reuse the same recovery code must fail
        reuse_resp = client.post("/api/auth/recover-password", json={
            "username": uname,
            "recovery_code": code_to_use,
            "new_password": "AnotherNewPassword789!"
        })
        self.assertEqual(reuse_resp.status_code, 400)
        self.assertTrue(
            "already" in reuse_resp.json()["error"]["message"].lower() or
            "invalid" in reuse_resp.json()["error"]["message"].lower()
        )

    def test_03_regenerate_recovery_codes_flow(self):
        """Test regenerating all 10 recovery codes requiring current password."""
        uname = f"regen_{uuid.uuid4().hex[:8]}"
        pwd = "RegenPassword123!"

        reg_resp = client.post("/api/auth/register", json={
            "username": uname,
            "password": pwd
        })
        token = reg_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Regenerate with wrong password fails
        bad_regen = client.post("/api/auth/regenerate-recovery-codes", headers=headers, json={
            "current_password": "WrongPassword123!"
        })
        self.assertEqual(bad_regen.status_code, 400)

        # Regenerate with correct password succeeds
        good_regen = client.post("/api/auth/regenerate-recovery-codes", headers=headers, json={
            "current_password": pwd
        })
        self.assertEqual(good_regen.status_code, 200)
        data = good_regen.json()
        self.assertIn("recovery_codes", data)
        self.assertEqual(len(data["recovery_codes"]), 10)

    def test_04_cross_user_report_isolation(self):
        """Test strict cross-user report isolation (User A report not accessible by User B)."""
        # Create User A
        user_a = Repository.create_user(
            username=f"user_a_{uuid.uuid4().hex[:6]}",
            password="UserAPassword123!",
            is_email_verified=True
        )
        token_a = create_access_token(user_a["id"], user_a["username"], True)

        # Create User B
        user_b = Repository.create_user(
            username=f"user_b_{uuid.uuid4().hex[:6]}",
            password="UserBPassword123!",
            is_email_verified=True
        )
        token_b = create_access_token(user_b["id"], user_b["username"], True)

        # Create report directly for User A
        report = Repository.create_report(
            user_id=user_a["id"],
            title="User A Confidential Neighborhood Audit",
            locality_name="Gachibowli, Hyderabad",
            lat=17.4401,
            lng=78.3489,
            comparison_locality_name=None,
            comparison_lat=None,
            comparison_lng=None,
            user_profile="family",
            user_priorities=["education", "safety"],
            sections_included=["summary", "amenities", "safety"],
            verification_hash="hash_user_a_123456",
            pdf_storage_path="backend/data/reports/fake_user_a.pdf",
            qr_code_url="https://locallens.app/verify/fake_user_a",
            raw_evidence=[],
            aggregated_metrics={},
            providers_used=[]
        )
        self.assertIsNotNone(report)
        report_id = report["id"]

        # 1. User A can retrieve their own report
        resp_a = client.get(f"/api/reports/{report_id}", headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.json()["id"], report_id)

        # 2. User B CANNOT retrieve User A's report (403 Forbidden or 404 Not Found)
        resp_b = client.get(f"/api/reports/{report_id}", headers={"Authorization": f"Bearer {token_b}"})
        self.assertIn(resp_b.status_code, [403, 404])

        # 3. Administrator CAN access User A's report
        resp_admin = client.get(f"/api/reports/{report_id}", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(resp_admin.status_code, 200)

    def test_05_razorpay_order_creation_and_hmac_verification(self):
        """Test Razorpay order creation (₹29 / 2900 paise) and HMAC-SHA256 signature verification."""
        user = Repository.create_user(
            username=f"payer_{uuid.uuid4().hex[:6]}",
            password="PayerPassword123!",
            is_email_verified=True
        )
        # Exhaust free credits
        conn = get_connection()
        conn.execute("UPDATE report_credits SET credits_remaining = 0 WHERE user_id = ?", (user["id"],))
        conn.commit()
        conn.close()

        token = create_access_token(user["id"], user["username"], True)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create order
        order_resp = client.post("/api/payments/create-order", headers=headers)
        self.assertEqual(order_resp.status_code, 200)
        order_data = order_resp.json()
        self.assertEqual(order_data["amount_paise"], 2900)
        self.assertEqual(order_data["amount_inr"], 29.0)
        self.assertEqual(order_data["currency"], "INR")
        order_id = order_data["order_id"]
        self.assertTrue(order_id.startswith("order_"))

        # 2. Verify payment signature with HMAC-SHA256
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = settings.RAZORPAY_KEY_SECRET or "locallens_test_secret"
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        valid_signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        # Temporary configure secret for deterministic HMAC test
        orig_secret = settings.RAZORPAY_KEY_SECRET
        settings.RAZORPAY_KEY_SECRET = secret
        try:
            # Bad signature -> 400
            bad_verify = client.post("/api/payments/verify-payment", headers=headers, json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": "invalid_signature_hex"
            })
            self.assertEqual(bad_verify.status_code, 400)

            # Valid signature -> 200
            good_verify = client.post("/api/payments/verify-payment", headers=headers, json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": valid_signature
            })
            self.assertEqual(good_verify.status_code, 200)
            verify_data = good_verify.json()
            self.assertTrue(verify_data["success"])
            self.assertEqual(verify_data["credits_remaining"], 1)

            # 3. Idempotent check: calling verify again with same payload succeeds without double crediting
            idempotent_resp = client.post("/api/payments/verify-payment", headers=headers, json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": valid_signature
            })
            self.assertEqual(idempotent_resp.status_code, 200)
            creds = Repository.get_credits(user["id"])
            self.assertEqual(creds["credits_remaining"], 1)
        finally:
            settings.RAZORPAY_KEY_SECRET = orig_secret

    def test_06_provider_health_diagnostics(self):
        """Test provider health endpoint accurately reflects keyless architecture without requiring Google Maps."""
        resp = client.get("/api/health/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("providers", data)

        providers = {p["id"]: p for p in data["providers"]}
        self.assertIn("maplibre_openfreemap", providers)
        self.assertEqual(providers["maplibre_openfreemap"]["status"], "operational")

        self.assertIn("osrm_routing", providers)
        self.assertEqual(providers["osrm_routing"]["status"], "operational")

        self.assertIn("open_meteo", providers)
        self.assertEqual(providers["open_meteo"]["status"], "operational")

        self.assertIn("telangana_spatial_db", providers)
        self.assertEqual(providers["telangana_spatial_db"]["status"], "operational")

        self.assertIn("water_cgwb", providers)
        self.assertEqual(providers["water_cgwb"]["status"], "operational")

        self.assertIn("safety_telangana", providers)
        self.assertEqual(providers["safety_telangana"]["status"], "operational")

        # Google Maps must not be required
        self.assertIn("google_maps", providers)
        self.assertIn(providers["google_maps"]["status"], ["not_required", "optional_configured"])

        # No sensitive secrets leaked
        raw_text = resp.text.lower()
        self.assertNotIn("secret", raw_text)
        self.assertNotIn("ai_token", raw_text)

    def test_07_admin_analytics_authorization(self):
        """Test admin analytics endpoint requires admin role."""
        # Non-admin user
        user = Repository.create_user(
            username=f"regular_{uuid.uuid4().hex[:6]}",
            password="RegularPassword123!",
            is_email_verified=True,
            is_admin=False
        )
        token = create_access_token(user["id"], user["username"], True, is_admin=False)

        # 1. Regular user gets 403 Forbidden
        regular_resp = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(regular_resp.status_code, 403)

        # 2. Admin user gets 200 OK with analytics data
        admin_resp = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(admin_resp.status_code, 200)
        data = admin_resp.json()
        self.assertIn("users", data)
        self.assertIn("activity", data)
        self.assertIn("payments", data)
        self.assertEqual(data["payments"]["report_price_inr"], 29)
        self.assertGreaterEqual(data["users"]["total_registered"], 1)

if __name__ == "__main__":
    unittest.main()
