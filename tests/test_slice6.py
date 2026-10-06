import unittest
import uuid
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token, decode_access_token

client = TestClient(app)

class TestSlice6AccountsAndCredits(unittest.TestCase):
    def setUp(self):
        self.test_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = "SecurePassword123!"
        self.test_name = "Alex Johnson"

    def test_user_registration_and_credits_lifecycle(self):
        # 1. Register new user
        reg_resp = client.post("/api/auth/register", json={
            "email": self.test_email,
            "password": self.test_password,
            "display_name": self.test_name
        })
        self.assertEqual(reg_resp.status_code, 200)
        data = reg_resp.json()
        token = data["access_token"]
        user = data["user"]
        self.assertEqual(user["email"], self.test_email)
        self.assertFalse(user["is_email_verified"])

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Check credits before verification -> must be 0
        creds_resp = client.get("/api/credits", headers=headers)
        self.assertEqual(creds_resp.status_code, 200)
        creds = creds_resp.json()
        self.assertEqual(creds["credits_remaining"], 0)
        self.assertFalse(creds["can_generate_report"])

        # 3. Simulate email verification -> must award 3 credits
        verify_resp = client.post("/api/auth/verify-email-simulate", headers=headers)
        self.assertEqual(verify_resp.status_code, 200)
        verified_data = verify_resp.json()
        self.assertTrue(verified_data["user"]["is_email_verified"])
        self.assertEqual(verified_data["credits"]["credits_remaining"], 3)
        self.assertTrue(verified_data["credits"]["can_generate_report"])

    def test_login_flow(self):
        # Create user directly
        user = Repository.create_user(self.test_email, self.test_password, self.test_name, is_email_verified=True)
        self.assertIsNotNone(user)

        # Login with correct password
        login_resp = client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

        # Login with wrong password
        fail_resp = client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "wrong_password"
        })
        self.assertEqual(fail_resp.status_code, 401)

    def test_saved_locations_crud(self):
        user = Repository.create_user(self.test_email, self.test_password, is_email_verified=True)
        token = create_access_token(user["id"], user["email"], True)
        headers = {"Authorization": f"Bearer {token}"}

        # Create
        create_resp = client.post("/api/saved-locations", headers=headers, json={
            "locality_name": "Koramangala, Bengaluru",
            "lat": 12.9352,
            "lng": 77.6245,
            "label": "Shortlist 1",
            "notes": "Near park and hospital"
        })
        self.assertEqual(create_resp.status_code, 200)
        loc_id = create_resp.json()["id"]

        # Read
        list_resp = client.get("/api/saved-locations", headers=headers)
        self.assertEqual(list_resp.status_code, 200)
        saved_list = list_resp.json()
        self.assertEqual(len(saved_list), 1)
        self.assertEqual(saved_list[0]["label"], "Shortlist 1")

        # Update
        update_resp = client.put(f"/api/saved-locations/{loc_id}", headers=headers, json={
            "label": "Top Choice",
            "notes": "Visited yesterday, good vibes"
        })
        self.assertEqual(update_resp.status_code, 200)

        # Delete
        del_resp = client.delete(f"/api/saved-locations/{loc_id}", headers=headers)
        self.assertEqual(del_resp.status_code, 200)

        # Verify empty
        list_resp2 = client.get("/api/saved-locations", headers=headers)
        self.assertEqual(len(list_resp2.json()), 0)

    def test_search_history_flow(self):
        user = Repository.create_user(self.test_email, self.test_password, is_email_verified=True)
        token = create_access_token(user["id"], user["email"], True)
        headers = {"Authorization": f"Bearer {token}"}

        # Record search
        add_resp = client.post("/api/search-history", headers=headers, json={
            "locality_name": "Indiranagar, Bengaluru",
            "lat": 12.9716,
            "lng": 77.5946,
            "provider": "Photon"
        })
        self.assertEqual(add_resp.status_code, 200)

        # List
        get_resp = client.get("/api/search-history", headers=headers)
        self.assertEqual(get_resp.status_code, 200)
        history = get_resp.json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["locality_name"], "Indiranagar, Bengaluru")

        # Clear
        clear_resp = client.delete("/api/search-history", headers=headers)
        self.assertEqual(clear_resp.status_code, 200)
        get_resp2 = client.get("/api/search-history", headers=headers)
        self.assertEqual(len(get_resp2.json()), 0)

    def test_preferences_update(self):
        user = Repository.create_user(self.test_email, self.test_password, is_email_verified=True)
        token = create_access_token(user["id"], user["email"], True)
        headers = {"Authorization": f"Bearer {token}"}

        put_resp = client.put("/api/preferences", headers=headers, json={
            "default_profile": "student",
            "default_priorities": ["education", "lifestyle"],
            "distance_preferences": [{"priority": "education", "preferred_distance_m": 800, "label": "Within 800m"}]
        })
        self.assertEqual(put_resp.status_code, 200)

        get_resp = client.get("/api/preferences", headers=headers)
        self.assertEqual(get_resp.status_code, 200)
        prefs = get_resp.json()
        self.assertEqual(prefs["default_profile"], "student")
        self.assertEqual(prefs["default_priorities"], ["education", "lifestyle"])

if __name__ == "__main__":
    unittest.main()
