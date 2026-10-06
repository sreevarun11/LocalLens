import os
import unittest
import uuid
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token
from backend.app.reports.pdf_generator import generate_report_pdf

client = TestClient(app)

class TestSlice7Reports(unittest.TestCase):
    def setUp(self):
        self.test_email = f"reporter_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = "Password123!"
        self.user = Repository.create_user(self.test_email, self.test_password, "Dr. Reporter", is_email_verified=True)
        self.token = create_access_token(self.user["id"], self.user["email"], True)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_pdf_generation_direct(self):
        out_path = os.path.join("data", "reports", f"test_{uuid.uuid4().hex[:6]}.pdf")
        res = generate_report_pdf(
            output_path=out_path,
            report_id="rep-unit-test-1",
            locality_name="Koramangala, Bengaluru",
            verification_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            verification_url="http://localhost:5173/verify/rep-unit-test-1",
            findings=[{"headline": "High density of healthcare", "detail": "3 clinics within 800m"}],
            amenity_rows=[{"category": "healthcare", "count": 5, "nearest_m": 250}],
            env_data={"aqi": 82, "pm25": 28.0, "pm10": 55.0},
            property_context={"property_address": "Flat 101, Palm Grove", "rent_or_price": "38,000"}
        )
        self.assertTrue(os.path.exists(res))
        self.assertTrue(os.path.getsize(res) > 1000)

    def test_report_generation_requires_verified_email(self):
        # Create unverified user
        unverified_email = f"unverified_{uuid.uuid4().hex[:8]}@example.com"
        unverified_user = Repository.create_user(unverified_email, self.test_password, is_email_verified=False)
        unverified_token = create_access_token(unverified_user["id"], unverified_email, False)

        resp = client.post("/api/reports/generate", headers={"Authorization": f"Bearer {unverified_token}"}, json={
            "locality_name": "Indiranagar, Bengaluru",
            "lat": 12.9784,
            "lng": 77.6408
        })
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Email verification required", resp.json()["error"]["message"])

    def test_report_generation_lifecycle_and_credit_deduction(self):
        # User starts with 3 credits
        initial_credits = Repository.get_credits(self.user["id"])
        self.assertEqual(initial_credits["credits_remaining"], 3)

        payload = {
            "locality_name": "Koramangala, Bengaluru",
            "lat": 12.9352,
            "lng": 77.6245,
            "user_profile": "family",
            "user_priorities": ["education", "healthcare"],
            "sections_included": ["summary", "amenities", "environment", "checklist", "sources"],
            "property_context": {
                "property_address": "Sample Villa 42",
                "rent_or_price": "60,000",
                "water_source_declared": "Cauvery piped",
                "user_notes": "Very quiet street"
            }
        }

        # 1. Generate Report
        resp = client.post("/api/reports/generate", headers=self.headers, json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        report_id = data["id"]
        self.assertIn("verification_hash", data)
        self.assertIn("pdf_url", data)
        self.assertEqual(data["credits_remaining"], 2)

        # 2. Check credits after generation
        updated_credits = Repository.get_credits(self.user["id"])
        self.assertEqual(updated_credits["credits_remaining"], 2)
        self.assertEqual(updated_credits["credits_used"], 1)

        # 3. Download generated PDF
        pdf_resp = client.get(f"/api/reports/{report_id}/pdf")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.headers["content-type"], "application/pdf")
        self.assertTrue(len(pdf_resp.content) > 1000)

        # 4. Public Verification Endpoint (Zero Auth required, no PII)
        verify_resp = client.get(f"/api/reports/verify/{report_id}")
        self.assertEqual(verify_resp.status_code, 200)
        v_data = verify_resp.json()
        self.assertEqual(v_data["status"], "valid")
        self.assertEqual(v_data["locality_name"], "Koramangala, Bengaluru")
        self.assertEqual(v_data["verification_hash"], data["verification_hash"])
        # Ensure zero user PII is exposed in verification output
        self.assertNotIn("email", v_data)
        self.assertNotIn(self.test_email, str(v_data))
        self.assertNotIn("Sample Villa 42", str(v_data))

        # 5. List user reports
        list_resp = client.get("/api/reports", headers=self.headers)
        self.assertEqual(list_resp.status_code, 200)
        reports = list_resp.json()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["id"], report_id)

    def test_report_fails_when_credits_exhausted(self):
        # Set credits to 0
        user_id = self.user["id"]
        Repository.deduct_credit(user_id)
        Repository.deduct_credit(user_id)
        Repository.deduct_credit(user_id)
        creds = Repository.get_credits(user_id)
        self.assertEqual(creds["credits_remaining"], 0)

        resp = client.post("/api/reports/generate", headers=self.headers, json={
            "locality_name": "Koramangala, Bengaluru",
            "lat": 12.9352,
            "lng": 77.6245
        })
        self.assertEqual(resp.status_code, 402)
        self.assertIn("credits", resp.json()["error"]["message"].lower())

if __name__ == "__main__":
    unittest.main()
