import unittest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.base import EvidenceItem, EvidenceEntity, EvidenceGap, DataSourceInfo
from backend.app.ai.input_sanitizer import sanitize_evidence_for_llm
from backend.app.ai.claim_validator import ClaimValidator
from backend.app.ai.deterministic_fallback import generate_deterministic_synthesis
from backend.app.evidence.personalization import Finding, VerifyOnSiteQuestion

client = TestClient(app)

class TestSlice5AISynthesis(unittest.TestCase):
    def setUp(self):
        self.mock_source = DataSourceInfo(
            name="OpenStreetMap",
            license="ODbL"
        )
        self.evidence_items = [
            EvidenceItem(
                id="loc1:education:nearest_distance_m",
                locality_key="loc1",
                module="education",
                metric="nearest_distance_m",
                value=450,
                unit="m",
                radius_m=1500,
                provenance_kind="map_listing",
                granularity="exact_place",
                source=self.mock_source,
                fetched_at=datetime.utcnow(),
                entities=[
                    EvidenceEntity(
                        name="National Public School",
                        lat=12.935,
                        lng=77.62,
                        distance_m=450,
                        category="education"
                    )
                ]
            ),
            EvidenceItem(
                id="loc1:environment:aqi",
                locality_key="loc1",
                module="environment",
                metric="aqi",
                value=78,
                unit="US AQI",
                provenance_kind="modeled_estimate",
                granularity="district",
                source=self.mock_source,
                fetched_at=datetime.utcnow()
            )
        ]
        self.gaps = [
            EvidenceGap(
                module="water",
                reason="No station within radius",
                granularity_needed="neighborhood"
            )
        ]
        self.evidence_map = {it.id: it for it in self.evidence_items}
        self.gap_ids = {f"gap:{g.module}" for g in self.gaps}
        self.allowed_names = {"Koramangala", "Bengaluru"}

    def test_input_sanitizer_strips_entities(self):
        sanitized = sanitize_evidence_for_llm(self.evidence_items, self.gaps)
        facts = sanitized["evidence_facts"]
        self.assertEqual(len(facts), 2)
        # Check that entity names are NOT in the sanitized output facts
        fact_str = str(facts)
        self.assertNotIn("National Public School", fact_str)
        self.assertEqual(facts[0]["metric"], "nearest_distance_m")
        self.assertEqual(facts[0]["value"], 450)
        self.assertEqual(facts[0]["evidence_id"], "loc1:education:nearest_distance_m")

    def test_claim_validator_passes_valid_statement(self):
        statement = {
            "text": "The nearest education facility is located 450 m away.",
            "kind": "observation",
            "evidence_ids": ["loc1:education:nearest_distance_m"]
        }
        valid, reason = ClaimValidator.validate_statement(
            statement, self.evidence_map, self.gap_ids, self.allowed_names
        )
        self.assertTrue(valid, f"Expected valid, got reason: {reason}")

    def test_claim_validator_rejects_banned_promotional_phrases(self):
        for phrase in ["This locality is the winner for families", "Safe neighborhood", "Ideal choice", "Best area"]:
            statement = {
                "text": phrase,
                "kind": "observation",
                "evidence_ids": ["loc1:education:nearest_distance_m"]
            }
            valid, reason = ClaimValidator.validate_statement(
                statement, self.evidence_map, self.gap_ids, self.allowed_names
            )
            self.assertFalse(valid, f"Expected rejection for '{phrase}', but it passed")
            self.assertIn("forbidden", reason.lower())

    def test_claim_validator_rejects_nonexistent_evidence_id(self):
        statement = {
            "text": "Nearest school is 450 meters away.",
            "kind": "observation",
            "evidence_ids": ["loc1:education:fabricated_metric_id"]
        }
        valid, reason = ClaimValidator.validate_statement(
            statement, self.evidence_map, self.gap_ids, self.allowed_names
        )
        self.assertFalse(valid)
        self.assertIn("non-existent evidence_id", reason)

    def test_claim_validator_rejects_invented_numbers(self):
        statement = {
            "text": "The nearest school is 950 meters away with an AQI of 24.",
            "kind": "observation",
            "evidence_ids": ["loc1:education:nearest_distance_m"]
        }
        valid, reason = ClaimValidator.validate_statement(
            statement, self.evidence_map, self.gap_ids, self.allowed_names
        )
        self.assertFalse(valid)
        self.assertIn("Invented number", reason)

    def test_deterministic_fallback_synthesis_always_passes_validation(self):
        findings = [
            Finding(
                id="f1",
                priority="education",
                status="available",
                headline="1 education facility within 1500 m",
                detail="Nearest education facility identified in this map database is 450 m away.",
                metric_name="nearest_distance_m",
                metric_value=450,
                within_preference="yes",
                evidence_ids=["loc1:education:nearest_distance_m"]
            )
        ]
        vos = [
            VerifyOnSiteQuestion(
                id="safety_lighting",
                priority_or_gap="safety_infrastructure",
                question="Are streetlights active along key pedestrian routes after dusk?",
                context="Street-level lighting infrastructure is not recorded in OSM."
            )
        ]
        fallback_json = generate_deterministic_synthesis(
            "Koramangala", findings, self.gaps, vos
        )
        self.assertIn("headline", fallback_json)
        self.assertIn("sections", fallback_json)
        self.assertTrue(len(fallback_json["sections"]) >= 1)

        # Validate with ClaimValidator
        cleaned_json, acceptable = ClaimValidator.validate_response(
            fallback_json, self.evidence_items, self.gaps, ["Koramangala"]
        )
        self.assertTrue(acceptable, "Deterministic fallback must pass ClaimValidator audit")
        self.assertEqual(len(cleaned_json["sections"]), len(fallback_json["sections"]))

    def test_ai_summarize_api_endpoint(self):
        payload = {
            "locality_name": "Koramangala, Bengaluru",
            "profile": "family",
            "priorities": ["education", "healthcare"],
            "distance_preferences": [
                {"priority": "education", "preferred_distance_m": 1000, "label": "Within 1 km"}
            ],
            "places_result": None,
            "environment_result": None,
            "water_result": None,
            "crime_result": None,
            "commute_result": None
        }
        resp = client.post("/api/ai/summarize", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("headline", data)
        self.assertIn("sections", data)
        self.assertIn("mode", data)
        self.assertIn(data["mode"], ["ai_grounded", "deterministic_fallback"])

if __name__ == "__main__":
    unittest.main()
