import os
import unittest
import asyncio
import tempfile
import uuid
from pypdf import PdfReader
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.providers.places import TelanganaPlacesProvider
from backend.app.providers.environment import get_cams_model_metadata, OpenMeteoAirQualityProvider
from backend.app.providers.safety import TelanganaSafetyProvider
from backend.app.reports.pdf_generator import generate_report_pdf
from backend.app.db.repository import Repository
from backend.app.db.local_db import get_connection
from backend.app.auth.tokens import create_access_token

client = TestClient(app)

class TestPhase2DefectsAndCorrectness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lat = 17.5047317
        cls.lng = 78.4252864
        cls.test_email = f"phase2_{uuid.uuid4().hex[:8]}@example.com"
        cls.test_pass = "Password123!"
        cls.user = Repository.create_user(cls.test_email, cls.test_pass, "Phase 2 Lead", is_email_verified=True)
        # Give report credits
        conn = get_connection()
        conn.execute("UPDATE report_credits SET credits_remaining = 10 WHERE user_id = ?", (cls.user["id"],))
        conn.commit()
        conn.close()
        cls.token = create_access_token(cls.user["id"], cls.user["email"], True)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_hyderabad_nonzero_amenities(self):
        """
        Defect #1 Regression Test:
        Known Hyderabad coordinates (lat 17.5047, lng 78.4253, HMWTSC area)
        must return non-zero facilities from the local dataset for multiple categories.
        Silently returning all zeros must fail this test.
        """
        tg_places = TelanganaPlacesProvider()
        self.assertTrue(tg_places.is_available(), "Telangana places DB must be available")
        self.assertTrue(tg_places.is_point_in_telangana(self.lat, self.lng))

        res = asyncio.run(tg_places.get_nearby_places(self.lat, self.lng, radius_m=1500))
        self.assertIn(res.status, ("available", "limited"))
        self.assertIsNotNone(res.data)
        self.assertGreater(len(res.data.places), 0, "Must return non-zero places for Hyderabad coordinates")
        counts = res.data.counts_by_category
        # Must have healthcare, education, and daily life facilities
        self.assertGreater(counts.get("healthcare", 0), 0, "Healthcare facilities must be non-zero")
        self.assertGreater(counts.get("education", 0), 0, "Education facilities must be non-zero")
        self.assertGreater(counts.get("daily_life", 0), 0, "Daily life facilities must be non-zero")
        self.assertGreater(counts.get("safety_infrastructure", 0), 0, "Safety facilities must be non-zero")

    def test_02_amenity_safety_unification(self):
        """
        Defect #2 Regression Test:
        Amenities summary and Safety section must agree.
        Both query paths must identify the nearby police facility (Jagadgirigutta PS).
        """
        safety_prov = TelanganaSafetyProvider()
        safety_res = asyncio.run(safety_prov.get_safety_and_crime_data(self.lat, self.lng, radius_m=1500))
        self.assertIsNotNone(safety_res.data)
        self.assertGreater(len(safety_res.data.nearby_facilities), 0)

        nearest_safety_facility = safety_res.data.nearby_facilities[0]
        self.assertIn("Jagadgirigutta", nearest_safety_facility.name)
        self.assertLess(nearest_safety_facility.distance_m, 600)

        # Now generate a report via API and verify the returned PDF rows and payload
        resp = client.post("/api/reports/generate", headers=self.headers, json={
            "locality_name": "HMWTSC",
            "lat": self.lat,
            "lng": self.lng
        })
        self.assertEqual(resp.status_code, 200, f"Report generation failed: {resp.text}")
        data = resp.json()
        report_id = data["id"]

        # Verify the report in database has non-zero safety and healthcare facilities
        rep = Repository.get_report_by_id(report_id)
        self.assertIsNotNone(rep)
        snapshot = rep.get("snapshot") or {}
        amenity_counts = snapshot.get("aggregated_metrics", {}).get("amenity_counts", {})
        self.assertGreater(amenity_counts.get("safety_infrastructure", 0), 0, "Safety count in report must be non-zero")
        self.assertGreater(amenity_counts.get("healthcare", 0), 0, "Healthcare count in report must be non-zero")

    def test_03_provider_failure_not_confident_zero(self):
        """
        Defect #3 Regression Test:
        Distinguish provider error / out-of-coverage from a confident zero count.
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Simulate an amenity row where provider had an error
            amenity_rows = [
                {"category": "healthcare", "count": None, "nearest_m": None, "status": "error"},
                {"category": "education", "count": 0, "nearest_m": None, "status": "limited"}
            ]
            pdf_path = generate_report_pdf(
                output_path=tmp_path,
                report_id="test-defect-3",
                locality_name="Test Locality",
                verification_hash="hash123",
                verification_url="http://localhost:5173/verify/test-defect-3",
                findings=[],
                amenity_rows=amenity_rows,
                env_data={"aqi": 50, "pm25": 12.0}
            )
            self.assertTrue(os.path.exists(pdf_path))
            reader = PdfReader(pdf_path)
            text = "".join([page.extract_text() for page in reader.pages])
            # Should contain "Unavailable" or "Provider query error", NOT a confident "0 facilities" for healthcare
            self.assertIn("Unavailable", text)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_04_cams_global_metadata_for_india(self):
        """
        Defect #4 Regression Test:
        Environmental resolution metadata for Indian coordinates must specify CAMS Global (~40 km),
        never European CAMS 11 km.
        """
        india_meta = get_cams_model_metadata(17.5047, 78.4253)
        self.assertEqual(india_meta["domain"], "cams_global")
        self.assertEqual(india_meta["resolution_km"], 40.0)
        self.assertIn("40 km", india_meta["description"])

        europe_meta = get_cams_model_metadata(48.8566, 2.3522)
        self.assertEqual(europe_meta["domain"], "cams_europe")
        self.assertEqual(europe_meta["resolution_km"], 11.0)

    def test_05_pdf_single_page_default(self):
        """
        PDF Redesign Specification:
        When no optional user property context or comparison is present,
        the generated PDF must be STRICTLY ONE PAGE.
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            amenity_rows = [
                {"category": "healthcare", "count": 12, "nearest_m": 240, "status": "available"},
                {"category": "education", "count": 8, "nearest_m": 410, "status": "available"},
                {"category": "safety_infrastructure", "count": 2, "nearest_m": 330, "status": "available"},
                {"category": "daily_life", "count": 25, "nearest_m": 120, "status": "available"},
                {"category": "transport", "count": 6, "nearest_m": 180, "status": "available"},
                {"category": "lifestyle", "count": 14, "nearest_m": 350, "status": "available"}
            ]
            pdf_path = generate_report_pdf(
                output_path=tmp_path,
                report_id="test-one-page",
                locality_name="HMWTSC, Ward 126 Jagathgirigutta, Hyderabad",
                verification_hash="hash-1page",
                verification_url="http://localhost:5173/verify/test-one-page",
                findings=[
                    {"headline": "High Healthcare Proximity", "detail": "12 healthcare facilities identified within 1.5 km."},
                    {"headline": "Transit Accessible", "detail": "6 transit stops within 1.5 km survey boundary."}
                ],
                amenity_rows=amenity_rows,
                env_data={"aqi": 72, "pm25": 24.5, "pm10": 42.0, "temperature_c": 26.5, "weather_desc": "Clear sky", "model_grid_resolution_km": 40.0},
                water_data={"district_name": "Medchal-Malkajgiri", "mandal_name": "Quthbullapur", "assessment_category": "Safe", "district_stage_of_extraction_pct": 58.2},
                safety_data={"nearby_facilities": [{"facility_type": "police", "name": "Jagadgirigutta Police Station", "distance_m": 330}]},
                property_context=None,  # No optional property context
                checklist_questions=None,
                comparison_name=None
            )
            self.assertTrue(os.path.exists(pdf_path))
            reader = PdfReader(pdf_path)
            self.assertEqual(len(reader.pages), 1, f"Expected exactly 1 page for default report, got {len(reader.pages)}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_06_pdf_max_two_pages_with_context(self):
        """
        PDF Redesign Specification:
        When user property context, comparison, and checklist are all present,
        the generated PDF must NOT exceed TWO PAGES.
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            amenity_rows = [
                {"category": "healthcare", "count": 12, "nearest_m": 240, "status": "available"},
                {"category": "education", "count": 8, "nearest_m": 410, "status": "available"},
                {"category": "safety_infrastructure", "count": 2, "nearest_m": 330, "status": "available"},
                {"category": "daily_life", "count": 25, "nearest_m": 120, "status": "available"},
                {"category": "transport", "count": 6, "nearest_m": 180, "status": "available"},
                {"category": "lifestyle", "count": 14, "nearest_m": 350, "status": "available"}
            ]
            pdf_path = generate_report_pdf(
                output_path=tmp_path,
                report_id="test-two-pages",
                locality_name="HMWTSC, Jagathgirigutta, Hyderabad",
                verification_hash="hash-2pages",
                verification_url="http://localhost:5173/verify/test-two-pages",
                findings=[
                    {"headline": "Verified Amenity Cluster", "detail": "Comprehensive facility coverage."},
                    {"headline": "Groundwater Classified Safe", "detail": "Recharge balance within sustainable parameters."}
                ],
                amenity_rows=amenity_rows,
                env_data={"aqi": 72, "pm25": 24.5, "pm10": 42.0, "temperature_c": 26.5, "weather_desc": "Clear sky", "model_grid_resolution_km": 40.0},
                water_data={"district_name": "Medchal-Malkajgiri", "mandal_name": "Quthbullapur", "assessment_category": "Safe", "district_stage_of_extraction_pct": 58.2},
                safety_data={"nearby_facilities": [{"facility_type": "police", "name": "Jagadgirigutta Police Station", "distance_m": 330}]},
                property_context={"property_address": "Block B, Green View Residency", "floor_level": "3rd Floor", "rent_or_price": "32,000"},
                checklist_questions=["Inspect tap pressure", "Test mobile 5G signal", "Check evening street lighting"],
                comparison_name="Kukatpally, Hyderabad"
            )
            self.assertTrue(os.path.exists(pdf_path))
            reader = PdfReader(pdf_path)
            self.assertEqual(len(reader.pages), 2, f"Expected exactly 2 pages with supplemental context, got {len(reader.pages)}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_07_pdf_omit_empty_property_fields(self):
        """
        PDF Specification:
        Unsupplied optional property fields must be completely omitted.
        No 'None', 'null', 'N/A', or placeholder labels.
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            pdf_path = generate_report_pdf(
                output_path=tmp_path,
                report_id="test-omit-fields",
                locality_name="Hyderabad Locality",
                verification_hash="hash-omit",
                verification_url="http://localhost:5173/verify/test-omit",
                findings=[],
                amenity_rows=[],
                env_data=None,
                property_context={
                    "property_address": "Villa 42, Palm Meadows",
                    "floor_level": "",  # Unsupplied
                    "unit_facing": None,  # Unsupplied
                    "water_source_declared": "None",  # Placeholder
                    "rent_or_price": "45,000"
                }
            )
            reader = PdfReader(pdf_path)
            text = "".join([page.extract_text() for page in reader.pages])
            self.assertIn("Villa 42, Palm Meadows", text)
            self.assertIn("45,000", text)
            # Ensure unsupplied field labels are NOT rendered
            self.assertNotIn("Floor Level", text)
            self.assertNotIn("Unit Facing", text)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_08_comparison_radius_propagation(self):
        """
        Locality Comparison Specification:
        Radius selector (e.g. 500, 1000, 2000 m) propagates from API to backend query,
        response metadata, and summary labels.
        """
        resp = client.post("/api/compare", json={
            "loc_a_name": "Charminar, Hyderabad",
            "loc_a_lat": 17.3616,
            "loc_a_lng": 78.4747,
            "loc_b_name": "Gachibowli, Hyderabad",
            "loc_b_lat": 17.4401,
            "loc_b_lng": 78.3489,
            "radius_m": 2000
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("radius_m"), 2000)
        # Check that count rows reflect 2 km radius in label
        count_rows = [r for r in data.get("rows", []) if r.get("metric") == "count_within_radius"]
        self.assertGreater(len(count_rows), 0)
        self.assertIn("2 km", count_rows[0].get("label"))

    def test_09_public_base_url_production_enforcement(self):
        """
        Public Base URL Specification:
        In production environment, resolving to localhost must fail loudly.
        """
        original_env = settings.ENVIRONMENT
        original_url = settings.PUBLIC_BASE_URL
        try:
            settings.ENVIRONMENT = "production"
            settings.PUBLIC_BASE_URL = "http://localhost:8000"
            with self.assertRaises(ValueError):
                settings.get_public_base_url()

            settings.PUBLIC_BASE_URL = "https://locallens.app"
            url = settings.get_public_base_url()
            self.assertEqual(url, "https://locallens.app")
        finally:
            settings.ENVIRONMENT = original_env
            settings.PUBLIC_BASE_URL = original_url


if __name__ == "__main__":
    unittest.main()
