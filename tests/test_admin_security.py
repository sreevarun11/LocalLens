import unittest
import uuid
import time
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token

client = TestClient(app)


class TestAdminSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Provision or retrieve platform admin sreevarun
        cls.admin_user = Repository.provision_admin_user(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
        assert cls.admin_user is not None, "Admin user must exist"
        assert bool(cls.admin_user["is_admin"]) is True, "Admin user must have is_admin=True in DB"

        cls.admin_token = create_access_token(
            user_id=cls.admin_user["id"],
            username_or_email=cls.admin_user["username"],
            is_email_verified=True,
            is_admin=True
        )

        # 2. Create a standard (non-admin) user
        cls.regular_username = f"user_{uuid.uuid4().hex[:8]}"
        cls.regular_password = "UserStrongPassword123!"
        cls.regular_user = Repository.create_user(
            username=cls.regular_username,
            password=cls.regular_password,
            display_name="Regular Citizen",
            email=f"{cls.regular_username}@example.com",
            is_admin=False,
            is_email_verified=True
        )
        assert bool(cls.regular_user["is_admin"]) is False, "Regular user must have is_admin=False in DB"

        cls.regular_token = create_access_token(
            user_id=cls.regular_user["id"],
            username_or_email=cls.regular_username,
            is_email_verified=True,
            is_admin=False
        )

    def test_01_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to admin/privileged endpoints must return 401 Unauthorized."""
        endpoints = [
            ("GET", "/api/admin/analytics"),
            ("GET", "/api/admin/diagnostics"),
            ("POST", "/api/credits/add", {"user_id": self.regular_user["id"], "amount": 10})
        ]

        for method, ep, *body in endpoints:
            if method == "GET":
                resp = client.get(ep)
            else:
                resp = client.post(ep, json=body[0] if body else {})
            self.assertEqual(
                resp.status_code, 401,
                f"Endpoint {ep} should return 401 for unauthenticated request, got {resp.status_code}"
            )

    def test_02_authenticated_regular_user_forbidden(self):
        """Authenticated ordinary users must receive 403 Forbidden on all admin and privileged endpoints."""
        headers = {"Authorization": f"Bearer {self.regular_token}"}

        # Admin analytics
        resp = client.get("/api/admin/analytics", headers=headers)
        self.assertEqual(resp.status_code, 403, f"Expected 403 on /api/admin/analytics, got {resp.status_code}")

        # Admin diagnostics
        resp = client.get("/api/admin/diagnostics", headers=headers)
        self.assertEqual(resp.status_code, 403, f"Expected 403 on /api/admin/diagnostics, got {resp.status_code}")

        # Privileged credit grant
        resp = client.post(
            "/api/credits/add",
            headers=headers,
            json={"user_id": self.regular_user["id"], "amount": 10}
        )
        self.assertEqual(resp.status_code, 403, f"Expected 403 on /api/credits/add, got {resp.status_code}")

    def test_03_authenticated_admin_allowed(self):
        """Authenticated administrator sreevarun must receive 200 OK on admin endpoints."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        resp = client.get("/api/admin/analytics", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("users", data)
        self.assertIn("activity", data)
        self.assertIn("payments", data)

        resp = client.get("/api/admin/diagnostics", headers=headers)
        self.assertEqual(resp.status_code, 200)
        diag = resp.json()
        self.assertIn("status", diag)
        self.assertIn("database", diag)
        self.assertIn("integrations", diag)

        # Admin granting credits
        resp = client.post(
            "/api/credits/add",
            headers=headers,
            json={"user_id": self.regular_user["id"], "amount": 5}
        )
        self.assertEqual(resp.status_code, 200)

    def test_04_forged_jwt_role_claim_rejected(self):
        """A forged JWT asserting is_admin=True for a regular user ID must be rejected with 403."""
        forged_token = create_access_token(
            user_id=self.regular_user["id"],
            username_or_email=self.regular_username,
            is_email_verified=True,
            is_admin=True  # Forged claim in token
        )
        headers = {"Authorization": f"Bearer {forged_token}"}

        resp = client.get("/api/admin/analytics", headers=headers)
        self.assertEqual(
            resp.status_code, 403,
            "Server-side DB check must override forged is_admin JWT claim and reject with 403"
        )

        resp = client.post(
            "/api/credits/add",
            headers=headers,
            json={"user_id": self.regular_user["id"], "amount": 50}
        )
        self.assertEqual(resp.status_code, 403)

    def _get_err(self, resp):
        data = resp.json()
        if isinstance(data, dict):
            if "error" in data and isinstance(data["error"], dict):
                return str(data["error"].get("message", ""))
            return str(data.get("detail", ""))
        return ""

    def test_05_reserved_admin_usernames_rejected_on_registration(self):
        """Public registration attempting to claim reserved administrator usernames must return 400."""
        reserved_usernames = ["sreevarun", "SreeVarun", "admin", "ADMINISTRATOR", "root"]
        for uname in reserved_usernames:
            resp = client.post("/api/auth/register", json={
                "username": uname,
                "display_name": "Intruder",
                "email": f"{uname.lower()}_{uuid.uuid4().hex[:4]}@intruder.com",
                "password": "StrongIntruderPassword123!"
            })
            self.assertEqual(
                resp.status_code, 400,
                f"Registration with reserved username '{uname}' should be rejected with 400, got {resp.status_code}"
            )
            self.assertIn("reserved", self._get_err(resp).lower())

    def test_06_expired_or_tampered_token_rejected(self):
        """Tampered or invalid tokens must return 401 Unauthorized."""
        # Tampered token
        tampered_token = self.admin_token[:-6] + "xxxxxx"
        resp = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(resp.status_code, 401)

        # Malformed header
        resp = client.get("/api/admin/analytics", headers={"Authorization": "InvalidScheme token"})
        self.assertEqual(resp.status_code, 401)

    def test_07_token_revocation_on_logout(self):
        """Logging in to get a session token, then calling logout must revoke the token so subsequent calls return 401."""
        login_user = f"logout_user_{uuid.uuid4().hex[:6]}"
        login_pwd = "LogoutUserPass123!"
        reg = client.post("/api/auth/register", json={
            "username": login_user,
            "display_name": "Logout Test",
            "email": f"{login_user}@example.com",
            "password": login_pwd
        })
        self.assertEqual(reg.status_code, 200)

        # Login to create an active session
        login_resp = client.post("/api/auth/login", json={
            "username": login_user,
            "password": login_pwd
        })
        self.assertEqual(login_resp.status_code, 200)
        session_token = login_resp.json()["access_token"]
        auth_hdr = {"Authorization": f"Bearer {session_token}"}

        # Check /api/auth/me works with this token
        me_resp = client.get("/api/auth/me", headers=auth_hdr)
        self.assertEqual(me_resp.status_code, 200)

        # Logout
        logout_resp = client.post("/api/auth/logout", headers=auth_hdr)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertTrue(logout_resp.json().get("success"))

        # Subsequent request using the revoked token must return 401
        after_resp = client.get("/api/auth/me", headers=auth_hdr)
        self.assertEqual(after_resp.status_code, 401, "Revoked token must return 401 Unauthorized")

    def test_08_failed_login_rate_limiting(self):
        """More than 5 consecutive failed login attempts within 60 seconds must return 429 Too Many Requests."""
        victim_username = f"target_{uuid.uuid4().hex[:6]}"
        # Ensure user exists so rate limit tracks the identifier
        reg = client.post("/api/auth/register", json={
            "username": victim_username,
            "display_name": "Target User",
            "email": f"{victim_username}@example.com",
            "password": "CorrectPassword123!"
        })
        self.assertEqual(reg.status_code, 200)

        # Attempt 5 incorrect logins
        for i in range(5):
            fail_resp = client.post("/api/auth/login", json={
                "username": victim_username,
                "password": "WrongPassword999!"
            })
            self.assertEqual(fail_resp.status_code, 401)

        # 6th attempt should be blocked with 429 Too Many Requests
        blocked_resp = client.post("/api/auth/login", json={
            "username": victim_username,
            "password": "WrongPassword999!"
        })
        self.assertEqual(
            blocked_resp.status_code, 429,
            f"Expected 429 Too Many Requests after 5 failed logins, got {blocked_resp.status_code}"
        )
        self.assertIn("too many failed login attempts", self._get_err(blocked_resp).lower())


if __name__ == "__main__":
    unittest.main()
