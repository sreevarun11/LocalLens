import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.base import ModuleResult, Coverage, DataSourceInfo
from backend.app.schemas.location import PlaceItem, PlacesData
from backend.app.schemas.modules import AirQualityData, CommuteData, CommuteModeResult
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.evidence.personalization import PersonalizationEngine, DistancePreference

class TestSlice3(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_evidence_builder_places(self):
        sample_places = [
            PlaceItem(
                id="osm_node_1",
                name="National Public School",
                category="education",
                lat=12.9360,
                lng=77.6250,
                distance_m=450,
                source_name="OpenStreetMap"
            ),
            PlaceItem(
                id="osm_node_2",
                name="St. John's Medical College Hospital",
                category="healthcare",
                lat=12.9310,
                lng=77.6210,
                distance_m=800,
                source_name="OpenStreetMap"
            )
        ]
        places_res = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(
                places=sample_places,
                counts_by_category={"education": 1, "healthcare": 1},
                radius_m=1500,
                cap_reached=False
            ),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=2, nearest_distance_m=450),
            limitations=[]
        )

        items, gaps = EvidenceBuilder.build_evidence(
            locality_key="loc1",
            places_res=places_res
        )

        self.assertTrue(len(items) > 0)
        edu_nearest = next((it for it in items if it.module == "education" and it.metric == "nearest_distance_m"), None)
        self.assertIsNotNone(edu_nearest)
        self.assertEqual(edu_nearest.value, 450)
        self.assertEqual(edu_nearest.unit, "meters")

    def test_distance_preference_evaluation(self):
        sample_places = [
            PlaceItem(
                id="osm_node_1",
                name="Local Academy",
                category="education",
                lat=12.9360,
                lng=77.6250,
                distance_m=1200,
                source_name="OpenStreetMap"
            )
        ]
        places_res = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(
                places=sample_places,
                counts_by_category={"education": 1},
                radius_m=1500,
                cap_reached=False
            ),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=1, nearest_distance_m=1200),
            limitations=[]
        )

        items, gaps = EvidenceBuilder.build_evidence("loc1", places_res=places_res)

        # 1. Preferred distance: 1500m -> 1200m is within preference ("yes")
        findings, _, _ = PersonalizationEngine.evaluate(
            evidence_items=items,
            gaps=gaps,
            profile="family",
            selected_priorities=["education"],
            distance_preferences=[DistancePreference(priority="education", preferred_distance_m=1500)]
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].within_preference, "yes")

        # 2. Preferred distance: 800m -> 1200m is beyond preference ("no")
        findings_beyond, _, _ = PersonalizationEngine.evaluate(
            evidence_items=items,
            gaps=gaps,
            profile="family",
            selected_priorities=["education"],
            distance_preferences=[DistancePreference(priority="education", preferred_distance_m=800)]
        )
        self.assertEqual(findings_beyond[0].within_preference, "no")
        self.assertIn("exceeds your 800m preference", findings_beyond[0].preference_note)

    def test_post_insights_api(self):
        payload = {
            "locality_key": "loc1",
            "profile": "family",
            "priorities": ["education", "healthcare", "safety_infrastructure"],
            "distance_preferences": [
                {"priority": "education", "preferred_distance_m": 2000}
            ]
        }
        resp = self.client.post("/api/insights", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("findings", data)
        self.assertIn("gap_callouts", data)
        self.assertIn("verify_on_site", data)
        # Verify Verify On Site items are present
        self.assertTrue(len(data["verify_on_site"]) > 0)
        self.assertIn("question", data["verify_on_site"][0])

if __name__ == "__main__":
    unittest.main()
