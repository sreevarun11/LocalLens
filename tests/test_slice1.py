import unittest
import asyncio
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.utils.geo import haversine_distance_m

class TestSlice1(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app"], "LocalLens")
        self.assertIn("flags", data)

    def test_provider_health_endpoint(self):
        resp = self.client.get("/api/health/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("providers", data)
        provider_ids = [p["id"] for p in data["providers"]]
        self.assertIn("google_maps", provider_ids)
        self.assertIn("osm_overpass", provider_ids)
        self.assertIn("open_meteo", provider_ids)
        self.assertIn("water_cgwb", provider_ids)
        self.assertIn("crime_ncrb", provider_ids)

    def test_autocomplete_endpoint(self):
        resp = self.client.get("/api/location/autocomplete?query=Koramangala")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        if len(data) > 0:
            self.assertIn("place_id", data[0])
            self.assertIn("description", data[0])

    def test_reverse_geocode_endpoint(self):
        resp = self.client.get("/api/location/reverse?lat=12.9352&lng=77.6245")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("name", data)
        self.assertAlmostEqual(data["lat"], 12.9352, places=2)
        self.assertAlmostEqual(data["lng"], 77.6245, places=2)

    def test_water_honest_unavailable_endpoint(self):
        resp = self.client.get("/api/modules/water?lat=12.9352&lng=77.6245")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["module"], "water")
        self.assertEqual(data["status"], "unavailable")
        self.assertIn("limitations", data)
        self.assertTrue(len(data["limitations"]) > 0)

    def test_crime_honest_unavailable_endpoint(self):
        resp = self.client.get("/api/modules/crime?lat=12.9352&lng=77.6245")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["module"], "crime")
        self.assertEqual(data["status"], "unavailable")
        # Verify absence caveat is present in limitations
        limitations_text = " ".join(data["limitations"])
        self.assertIn("does not imply", limitations_text)

    def test_haversine_distance(self):
        # Koramangala to Indiranagar: approx 5.5 - 6.0 km
        dist = haversine_distance_m(12.9352, 77.6245, 12.9811, 77.6444)
        self.assertTrue(5000 <= dist <= 6500)

if __name__ == "__main__":
    unittest.main()
