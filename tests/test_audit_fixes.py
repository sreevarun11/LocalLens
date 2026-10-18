import unittest
import os
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.repository import Repository
from backend.app.config import settings

class TestAuditFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_admin_elevation_and_analytics_authorization(self):
        """Verify that registering with username 'sreevarun' automatically grants admin rights and grants access to /api/admin/analytics."""
        # 1. Create a regular non-admin user
        reg_username = f"reg_user_{uuid.uuid4().hex[:6]}"
        reg_user = Repository.create_user(
            username=reg_username,
            password="StrongPassword123!",
            display_name="Regular User",
            is_email_verified=True,
            is_admin=False
        )
        self.assertIsNotNone(reg_user)
        self.assertFalse(reg_user["is_admin"])

        # Login as regular user
        login_res = self.client.post("/api/auth/login", json={
            "username": reg_username,
            "password": "StrongPassword123!"
        })
        self.assertEqual(login_res.status_code, 200)
        reg_token = login_res.json()["access_token"]

        # Attempt to access /api/admin/analytics as regular user -> must be 403 Forbidden
        admin_res_forbidden = self.client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {reg_token}"}
        )
        self.assertEqual(admin_res_forbidden.status_code, 403)

        # 2. Register or fetch admin user 'sreevarun'
        admin_username = "sreevarun"
        # Check if already exists or create
        existing_admin = Repository.get_user_by_id("some-dummy")
        admin_user = Repository.create_user(
            username=admin_username,
            password="AdminStrongPassword123!",
            display_name="Maheshwaram Sree Varun",
            is_email_verified=True,
            is_admin=False  # Should be automatically elevated because username == sreevarun
        )
        if admin_user is None:
            # Already created in a prior run; authenticate
            admin_auth = Repository.authenticate_user(admin_username, "AdminStrongPassword123!")
            self.assertIsNotNone(admin_auth)
            self.assertTrue(admin_auth["is_admin"])
        else:
            self.assertTrue(admin_user["is_admin"], "User 'sreevarun' must be automatically elevated to admin")

        # Login as admin user
        admin_login = self.client.post("/api/auth/login", json={
            "username": admin_username,
            "password": "AdminStrongPassword123!"
        })
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["access_token"]
        self.assertTrue(admin_login.json()["user"]["is_admin"])

        # Access /api/admin/analytics as admin -> must be 200 OK
        admin_res_ok = self.client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(admin_res_ok.status_code, 200)
        data = admin_res_ok.json()
        self.assertIn("users", data)
        self.assertIn("activity", data)
        self.assertIn("payments", data)

        # Verify real database collections in analytics response
        self.assertIn("recent_registrations", data["users"])
        self.assertIsInstance(data["users"]["recent_registrations"], list)
        self.assertIn("recent_reports", data["activity"])
        self.assertIsInstance(data["activity"]["recent_reports"], list)
        self.assertIn("recent_payments", data["payments"])
        self.assertIsInstance(data["payments"]["recent_payments"], list)

    def test_02_searchbar_demo_localities(self):
        """Verify SearchBar.tsx demo localities are strictly Telangana cities: Hyderabad, Nizamabad, and Mancherial."""
        searchbar_path = os.path.join("frontend", "src", "components", "search", "SearchBar.tsx")
        with open(searchbar_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("handleDemoSelect('Hyderabad')", content)
        self.assertIn("handleDemoSelect('Nizamabad')", content)
        self.assertIn("handleDemoSelect('Mancherial')", content)

        # Ensure legacy Bengaluru demo localities were removed from SearchBar demo chips
        self.assertNotIn("Koramangala, Bengaluru", content)
        self.assertNotIn("Indiranagar, Bengaluru", content)
        self.assertNotIn("Chandapura, Bengaluru", content)

    def test_03_explore_page_locality_insight_removal_and_dynamic_radius(self):
        """Verify Section 4 Locality Insight is removed and no hardcoded 1,500m remains in ExplorePage.tsx."""
        explore_path = os.path.join("frontend", "src", "pages", "ExplorePage.tsx")
        with open(explore_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Section 4 Locality Insight must be completely removed
        self.assertNotIn("Locality Insight", content)
        self.assertNotIn("Evidence-Based Analysis", content)
        self.assertNotIn("Evidence Synthesis Methodology", content)
        self.assertNotIn("WHAT WE FOUND", content)
        self.assertNotIn("WHAT IS LIMITED", content)
        self.assertNotIn("WHAT IS UNAVAILABLE", content)

        # No hardcoded 1,500m or 1500m in ExplorePage.tsx category text
        self.assertNotIn("1,500m", content)
        self.assertNotIn("1500m.", content)

        # Dynamic radius expressions must be present
        self.assertIn("placesResult?.coverage?.radius_m || surveyRadius", content)

    def test_04_compare_page_dynamic_radius_and_placeholders(self):
        """Verify ComparePage.tsx has dynamic radius and Telangana locality placeholders."""
        compare_path = os.path.join("frontend", "src", "pages", "ComparePage.tsx")
        with open(compare_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Search first locality (e.g. Hyderabad)", content)
        self.assertIn("Search second locality (e.g. Nizamabad)", content)
        self.assertNotIn("Search first locality (e.g. Koramangala)", content)
        self.assertNotIn("Search second locality (e.g. Indiranagar)", content)

        # Dynamic comparison table radius
        self.assertIn("radiusM >= 1000", content)
        self.assertNotIn("Identical radius: 1500m straight-line distance", content)

    def test_05_footer_attribution(self):
        """Verify App.tsx footer has exact required attribution and Admin navigation."""
        app_path = os.path.join("frontend", "src", "App.tsx")
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Created with purpose by Maheshwaram Sree Varun", content)
        self.assertIn("© 2026 LocalLens. All rights reserved.", content)
        self.assertIn('<Link to="/admin" className="hover:text-teal-700">Admin</Link>', content)

    def test_06_payments_page_owner_fix_preserved(self):
        """Verify PaymentsPage.tsx preserves the owner's manual fix and does not simulate checkout."""
        payments_path = os.path.join("frontend", "src", "pages", "PaymentsPage.tsx")
        with open(payments_path, "r", encoding="utf-8") as f:
            content = f.read()

        # The explicit owner error must be intact
        self.assertIn("Razorpay checkout is unavailable or payment configuration is incomplete", content)
        self.assertIn("No payment was made. Please try again later.", content)
        # Simulated payment verification fallback must NOT exist
        self.assertNotIn("verifyPayment({ razorpay_order_id: order.id, razorpay_payment_id: 'pay_simulated'", content)

if __name__ == "__main__":
    unittest.main()
