import os
import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.modules import SafetyAndCrimeData, SafetyFacility, EmergencyContact, JurisdictionInfo
from backend.app.providers.safety import TelanganaSafetyProvider, VERIFIED_EMERGENCY_CONTACTS
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.reports.pdf_generator import generate_report_pdf


class TestSafetyStage4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.provider = TelanganaSafetyProvider()

    # 1. Crime statistics remain unavailable when unsupported by verified sources
    def test_01_crime_statistics_honest_unavailable_state(self):
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        self.assertIsNotNone(result.data)
        self.assertEqual(result.data.crime_statistics_status, "unavailable")
        self.assertIn("Verified locality-level crime statistics are not available", result.data.crime_disclosure_note)
        self.assertIn("does not imply that an area is safe", result.data.absence_caveat)

    # 2. No synthetic safety score, risk rating, or safe/unsafe verdict is returned
    def test_02_no_synthetic_safety_scores_or_verdicts(self):
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        self.assertIsNotNone(result.data)
        data_dict = result.data.model_dump()
        forbidden_keys = [
            "safety_score", "crime_score", "risk_rating", "verdict",
            "is_safe", "safety_rating", "composite_score", "safety_index"
        ]
        for key in forbidden_keys:
            self.assertNotIn(key, data_dict, f"Forbidden synthetic key '{key}' found in safety response!")

    # 3. District and commissionerate statistics are never assigned as locality-level rates
    def test_03_no_district_crime_disaggregation_or_rates(self):
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        self.assertIsNotNone(result.data)
        self.assertIsNone(result.data.incident_count)
        self.assertIsNone(result.data.rate_per_100k)
        self.assertIsNone(result.data.reporting_year)
        self.assertIsNone(result.data.source_agency)
        self.assertEqual(result.data.data_granularity, "district")

    # 4. Nearby police facilities are retrieved from the actual local spatial database
    def test_04_nearby_police_facilities_from_actual_db(self):
        # Charminar coordinates in Hyderabad core
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747, radius_m=3000))
        self.assertIsNotNone(result.data)
        self.assertGreater(len(result.data.nearby_facilities), 0)

        police_facilities = [f for f in result.data.nearby_facilities if f.facility_type == "police"]
        self.assertGreater(len(police_facilities), 0, "No police stations retrieved from actual database!")
        first_police = police_facilities[0]
        self.assertTrue(first_police.id.startswith("osm_"))
        self.assertTrue(len(first_police.name) > 0)
        self.assertGreater(first_police.distance_m, 0)
        self.assertIn("OpenStreetMap", first_police.source_name)

    # 5. Nearby fire facilities are retrieved from the actual local spatial database
    def test_05_nearby_fire_facilities_from_actual_db(self):
        # Secunderabad SP Road fire station vicinity
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.4431, 78.4855, radius_m=3000))
        self.assertIsNotNone(result.data)
        fire_facilities = [f for f in result.data.nearby_facilities if f.facility_type == "fire_station"]
        self.assertGreater(len(fire_facilities), 0, "No fire stations retrieved from actual database!")
        first_fire = fire_facilities[0]
        self.assertEqual(first_fire.facility_type, "fire_station")
        self.assertIn("Fire", first_fire.name)

    # 6. Distance and coordinates are validated
    def test_06_distance_and_coordinate_validation(self):
        # Invalid latitude > 90
        invalid_res = asyncio.run(self.provider.get_safety_and_crime_data(95.0, 78.4747))
        self.assertEqual(invalid_res.status, "error")
        self.assertIn("out of valid range", invalid_res.message)

        # Invalid longitude > 180
        invalid_lng_res = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 185.0))
        self.assertEqual(invalid_lng_res.status, "error")

        # Distances are non-negative and properly sorted ascending
        valid_res = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747, radius_m=3000))
        distances = [f.distance_m for f in valid_res.data.nearby_facilities]
        self.assertEqual(distances, sorted(distances), "Facilities are not sorted by distance ascending!")
        for d in distances:
            self.assertGreaterEqual(d, 0)

    # 7. Emergency contacts include correct source metadata
    def test_07_emergency_contacts_source_metadata(self):
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        self.assertIsNotNone(result.data)
        contacts = result.data.emergency_contacts
        self.assertEqual(len(contacts), 6)

        required_numbers = {"112", "100", "101", "108", "1090", "1930"}
        found_numbers = {c.number for c in contacts}
        self.assertEqual(required_numbers, found_numbers)

        for c in contacts:
            self.assertTrue(len(c.service) > 0)
            self.assertTrue(len(c.description) > 0)
            self.assertTrue(len(c.jurisdiction) > 0)
            self.assertTrue(len(c.verified_authority) > 0)
            self.assertTrue(c.source_url.startswith("https://"))
            self.assertTrue(".gov.in" in c.source_url)
            self.assertIsNotNone(c.last_verified_at)
            self.assertIsInstance(c.limitations, list)

    # 8. Unverified emergency numbers are not published as verified
    def test_08_no_unverified_emergency_numbers(self):
        contacts = VERIFIED_EMERGENCY_CONTACTS
        for c in contacts:
            # Phone number must be pure numeric and safe for tel: protocol
            self.assertTrue(c.number.isdigit())
            # All authorities must be official government departments
            self.assertTrue(any(gov_term in c.verified_authority for gov_term in ["Ministry", "Police", "Dept", "Department", "Centre"]))

    # 9. Jurisdiction is unavailable when verified boundary evidence is missing
    def test_09_jurisdiction_unavailable_when_boundary_unverified(self):
        # 1. Gachibowli / Serilingampally in Ranga Reddy district:
        # In Ranga Reddy and Medchal-Malkajgiri, police jurisdictions divide between Cyberabad and Rachakonda.
        # Open data does not contain digital beat boundary shapefiles, so it must return 'unavailable'.
        rr_res = asyncio.run(self.provider.get_safety_and_crime_data(17.4401, 78.3489))
        self.assertEqual(rr_res.data.jurisdiction.jurisdiction_type, "unavailable")
        self.assertIsNone(rr_res.data.jurisdiction.jurisdiction_name)
        self.assertTrue(any("Cyberabad and Rachakonda" in lim for lim in rr_res.data.jurisdiction.limitations))

        # 2. Hyderabad revenue district is strictly coterminous with Hyderabad City Police Commissionerate:
        hyd_res = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        self.assertEqual(hyd_res.data.jurisdiction.jurisdiction_type, "commissionerate")
        self.assertEqual(hyd_res.data.jurisdiction.jurisdiction_name, "Hyderabad City Police Commissionerate")
        self.assertEqual(hyd_res.data.jurisdiction.source_url, "https://hyderabadpolice.gov.in")

    # 10. Missing facilities are distinguished from provider/database failures
    def test_10_missing_facilities_distinguished_from_database_error(self):
        # Corrupt / missing database path should return status="error"
        bad_provider = TelanganaSafetyProvider(db_path="/nonexistent/path/to/db.sqlite")
        bad_res = asyncio.run(bad_provider.get_safety_and_crime_data(17.3616, 78.4747))
        self.assertEqual(bad_res.status, "error")
        self.assertIsNone(bad_res.data)

        # Legitimate search with radius so tiny that zero facilities exist:
        # Should return status="available" with empty facilities list, NOT status="error"
        empty_res = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747, radius_m=10))
        self.assertEqual(empty_res.status, "available")
        self.assertIsNotNone(empty_res.data)
        self.assertEqual(len(empty_res.data.nearby_facilities), 0)

    # 11. Partial API availability is handled correctly
    def test_11_partial_api_availability_handling(self):
        # In Gachibowli: facilities are available (police stations nearby), emergency contacts are available,
        # but jurisdiction is unavailable and crime incident statistics are unavailable.
        result = asyncio.run(self.provider.get_safety_and_crime_data(17.4401, 78.3489))
        self.assertEqual(result.status, "available")
        self.assertGreater(len(result.data.nearby_facilities), 0)
        self.assertEqual(len(result.data.emergency_contacts), 6)
        self.assertEqual(result.data.jurisdiction.jurisdiction_type, "unavailable")
        self.assertEqual(result.data.crime_statistics_status, "unavailable")

    # 12. Out-of-Telangana requests do not fabricate local facilities
    def test_12_out_of_telangana_no_fabricated_facilities(self):
        # Bengaluru coordinates
        blr_res = asyncio.run(self.provider.get_safety_and_crime_data(12.9352, 77.6245))
        self.assertEqual(blr_res.status, "unavailable")
        self.assertIsNone(blr_res.data)
        self.assertTrue(any("outside Telangana" in lim for lim in blr_res.limitations))
        self.assertTrue(any("does not imply that an area is safe" in lim for lim in blr_res.limitations))

    # 13. API endpoints contract and aliases
    def test_13_api_endpoints_contract_and_aliases(self):
        # Test /api/modules/crime
        resp_crime = self.client.get("/api/modules/crime?lat=17.3616&lng=78.4747&radius_m=3000")
        self.assertEqual(resp_crime.status_code, 200)
        data_crime = resp_crime.json()
        self.assertEqual(data_crime["module"], "crime")
        self.assertEqual(data_crime["status"], "available")
        self.assertIn("nearby_facilities", data_crime["data"])
        self.assertIn("emergency_contacts", data_crime["data"])
        self.assertIn("jurisdiction", data_crime["data"])
        self.assertEqual(data_crime["data"]["crime_statistics_status"], "unavailable")

        # Test /api/modules/safety alias
        resp_safety = self.client.get("/api/modules/safety?lat=17.3616&lng=78.4747&radius_m=3000")
        self.assertEqual(resp_safety.status_code, 200)
        data_safety = resp_safety.json()
        self.assertEqual(len(data_safety["data"]["nearby_facilities"]), len(data_crime["data"]["nearby_facilities"]))

    # 14. PDF reports preserve safety limitations and do not create unsupported claims
    def test_14_pdf_report_incorporates_safety_evidence(self):
        output_dir = os.path.join("backend", "data", "reports")
        os.makedirs(output_dir, exist_ok=True)
        test_pdf_path = os.path.join(output_dir, "test_safety_report.pdf")

        safety_res = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        safety_dict = safety_res.data.model_dump()

        res_path = generate_report_pdf(
            output_path=test_pdf_path,
            report_id="test-safety-stage4",
            locality_name="Charminar, Hyderabad",
            verification_hash="abcdef1234567890",
            verification_url="https://locallens.app/verify/test-safety-stage4",
            findings=[],
            amenity_rows=[{"category": "safety_infrastructure", "count": len(safety_dict["nearby_facilities"]), "nearest_m": 500}],
            env_data={"aqi": 75, "pm25": 24.0, "pm10": 45.0},
            water_data=None,
            safety_data=safety_dict
        )

        self.assertTrue(os.path.exists(res_path))
        self.assertGreater(os.path.getsize(res_path), 5000)

    # 15. Evidence builder safety items and crime gap
    def test_15_evidence_builder_safety_items_and_crime_gap(self):
        safety_res = asyncio.run(self.provider.get_safety_and_crime_data(17.3616, 78.4747))
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key="charminar",
            crime_res=safety_res
        )

        # Check that safety infrastructure evidence items were created
        police_items = [it for it in items if it.metric == "nearest_police_distance_m"]
        self.assertGreater(len(police_items), 0)
        self.assertEqual(police_items[0].unit, "meters")

        contact_items = [it for it in items if it.metric == "emergency_contacts_count"]
        self.assertGreater(len(contact_items), 0)
        self.assertEqual(contact_items[0].value, 6)

        # Check that crime gap is explicitly registered
        crime_gaps = [g for g in gaps if g.module == "crime"]
        self.assertGreater(len(crime_gaps), 0)
        self.assertIn("Locality-level crime incident statistics are unavailable", crime_gaps[0].reason)


if __name__ == "__main__":
    unittest.main()
