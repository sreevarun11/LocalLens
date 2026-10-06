import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.base import ModuleResult, Coverage, DataSourceInfo
from backend.app.schemas.location import PlaceItem, PlacesData
from backend.app.evidence.comparison import ComparisonEngine

class TestSlice4(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_comparability_same_provider(self):
        places_a = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(
                places=[PlaceItem(id="1", name="School A", category="education", lat=12.9, lng=77.6, distance_m=400, source_name="OpenStreetMap")],
                counts_by_category={"education": 1},
                radius_m=1500,
                cap_reached=False
            ),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=1, nearest_distance_m=400),
            limitations=[]
        )
        places_b = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(
                places=[PlaceItem(id="2", name="School B", category="education", lat=12.98, lng=77.64, distance_m=1200, source_name="OpenStreetMap")],
                counts_by_category={"education": 1},
                radius_m=1500,
                cap_reached=False
            ),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=1, nearest_distance_m=1200),
            limitations=[]
        )

        summary = ComparisonEngine.compare_localities(
            loc_a_name="Koramangala",
            loc_b_name="Indiranagar",
            places_a=places_a,
            places_b=places_b,
            env_a=None, env_b=None, water_a=None, water_b=None, crime_a=None, crime_b=None,
            priorities=["education"]
        )

        edu_row = next((r for r in summary.rows if r.priority == "education" and r.metric == "nearest_distance_m"), None)
        self.assertIsNotNone(edu_row)
        self.assertEqual(edu_row.comparability, "comparable")
        self.assertIn("Koramangala has a facility within 400m", edu_row.difference_statement)

        # Check banned words in output
        banned = ["winner", "best", "safe", "ideal", "score", "perfect"]
        full_text = " ".join(summary.key_differences + [r.difference_statement or "" for r in summary.rows]).lower()
        for b in banned:
            self.assertNotIn(b, full_text)

    def test_comparability_different_providers(self):
        places_a = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(places=[], counts_by_category={}, radius_m=1500),
            sources=[DataSourceInfo(name="Google Places")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=0),
            limitations=[]
        )
        places_b = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(places=[], counts_by_category={}, radius_m=1500),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=0),
            limitations=[]
        )

        summary = ComparisonEngine.compare_localities(
            loc_a_name="Loc A", loc_b_name="Loc B",
            places_a=places_a, places_b=places_b,
            env_a=None, env_b=None, water_a=None, water_b=None, crime_a=None, crime_b=None,
            priorities=["education"]
        )

        edu_row = next((r for r in summary.rows if r.priority == "education"), None)
        self.assertIsNotNone(edu_row)
        self.assertEqual(edu_row.comparability, "not_comparable")
        self.assertIn("Different data sources", edu_row.comparability_reason)

    def test_comparability_capped_counts(self):
        places_a = ModuleResult[PlacesData](
            module="places",
            status="limited",
            provenance_kind="map_listing",
            data=PlacesData(places=[], counts_by_category={"education": 60}, radius_m=1500, cap_reached=True),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=60, result_cap_reached=True),
            limitations=[]
        )
        places_b = ModuleResult[PlacesData](
            module="places",
            status="limited",
            provenance_kind="map_listing",
            data=PlacesData(places=[], counts_by_category={"education": 60}, radius_m=1500, cap_reached=True),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=60, result_cap_reached=True),
            limitations=[]
        )

        summary = ComparisonEngine.compare_localities(
            loc_a_name="Loc A", loc_b_name="Loc B",
            places_a=places_a, places_b=places_b,
            env_a=None, env_b=None, water_a=None, water_b=None, crime_a=None, crime_b=None,
            priorities=["education"]
        )

        count_row = next((r for r in summary.rows if r.priority == "education" and r.metric == "count_within_radius"), None)
        self.assertIsNotNone(count_row)
        self.assertEqual(count_row.comparability, "partly_comparable")
        self.assertIn("reached the provider result limit", count_row.difference_statement)

    def test_compare_api_endpoint(self):
        req = {
            "loc_a_name": "Koramangala",
            "loc_a_lat": 12.9352,
            "loc_a_lng": 77.6245,
            "loc_b_name": "Indiranagar",
            "loc_b_lat": 12.9811,
            "loc_b_lng": 77.6444,
            "priorities": ["education", "environment"],
            "load_water_crime": False
        }
        resp = self.client.post("/api/compare", json=req)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("key_differences", data)
        self.assertIn("rows", data)
        self.assertTrue(len(data["rows"]) > 0)

if __name__ == "__main__":
    unittest.main()
