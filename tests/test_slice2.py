import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestSlice2(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_environment_module(self):
        # Koramangala
        resp = self.client.get("/api/modules/environment?lat=12.9352&lng=77.6245")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["module"], "environment")
        self.assertIn(data["status"], ["available", "limited"])
        self.assertIn("data", data)
        self.assertIn("pm25", data["data"])
        self.assertIn("pm10", data["data"])
        self.assertIn("limitations", data)
        # Verify mandatory modeled disclosure
        lim_text = " ".join(data["limitations"])
        self.assertIn("Modeled estimate", lim_text)

    def test_places_sorting_and_schema(self):
        resp = self.client.get("/api/modules/places?lat=12.9352&lng=77.6245&radius_m=1000")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["module"], "places")
        self.assertIn("data", data)
        places = data["data"].get("places", [])
        if len(places) > 1:
            # Check sorted strictly by distance ascending
            for i in range(len(places) - 1):
                self.assertLessEqual(places[i]["distance_m"], places[i + 1]["distance_m"])

    def test_water_honest_unavailable_schema(self):
        resp = self.client.get("/api/modules/water?lat=12.8009&lng=77.7115")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "unavailable")
        self.assertEqual(data["provenance_kind"], "official_dataset")

    def test_crime_honest_absence_caveat(self):
        resp = self.client.get("/api/modules/crime?lat=12.8009&lng=77.7115")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "unavailable")
        lim_text = " ".join(data["limitations"])
        self.assertIn("does not imply that an area is safe", lim_text)

    def test_demo_localities_resolution(self):
        # Test autocomplete returns valid place_id for demo localities
        for demo in ["Koramangala", "Indiranagar", "Chandapura"]:
            resp = self.client.get(f"/api/location/autocomplete?query={demo}")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertGreater(len(data), 0, f"Failed for {demo}")
            self.assertIn("place_id", data[0])

if __name__ == "__main__":
    unittest.main()
