import unittest
import os
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.providers.places import TelanganaPlacesProvider
from scripts.build_telangana_places_db import map_osm_tags

class TestTelanganaPlaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.provider = TelanganaPlacesProvider()

    def test_provider_availability_and_metadata(self):
        self.assertTrue(self.provider.is_available(), "Telangana places database must exist and be accessible")
        meta = self.provider.get_metadata()
        self.assertIn("dataset_source", meta)
        self.assertIn("dataset_timestamp", meta)
        self.assertIn("license", meta)
        self.assertEqual(meta["license"], "Open Database License (ODbL) 1.0")
        total = int(meta.get("total_facilities", 0))
        self.assertGreater(total, 20000, "Database should contain at least 20,000 facilities")

    def test_bounding_envelope_detection(self):
        # Hyderabad (inside Telangana)
        self.assertTrue(self.provider.is_point_in_telangana(17.3616, 78.4747))
        # Warangal (inside Telangana)
        self.assertTrue(self.provider.is_point_in_telangana(17.9784, 79.5941))
        # Alampur (inside Telangana, southern border)
        self.assertTrue(self.provider.is_point_in_telangana(15.8778, 78.1311))
        # Adilabad (inside Telangana, northern border)
        self.assertTrue(self.provider.is_point_in_telangana(19.6640, 78.5320))
        # Bangalore (outside Telangana)
        self.assertFalse(self.provider.is_point_in_telangana(12.9352, 77.6245))
        # Delhi (outside Telangana)
        self.assertFalse(self.provider.is_point_in_telangana(28.6139, 77.2090))

    def test_osm_tag_to_category_mapping(self):
        # Healthcare
        cat, sub = map_osm_tags({"amenity": "hospital"})
        self.assertEqual(cat, "healthcare")
        self.assertEqual(sub, "hospital")

        cat, sub = map_osm_tags({"amenity": "clinic"})
        self.assertEqual(cat, "healthcare")

        cat, sub = map_osm_tags({"shop": "chemist"})
        self.assertEqual(cat, "healthcare")

        # Education
        cat, sub = map_osm_tags({"amenity": "school"})
        self.assertEqual(cat, "education")

        cat, sub = map_osm_tags({"amenity": "university"})
        self.assertEqual(cat, "education")

        # Safety Infrastructure
        cat, sub = map_osm_tags({"amenity": "police"})
        self.assertEqual(cat, "safety_infrastructure")

        cat, sub = map_osm_tags({"amenity": "fire_station"})
        self.assertEqual(cat, "safety_infrastructure")

        # Daily Essentials
        cat, sub = map_osm_tags({"shop": "supermarket"})
        self.assertEqual(cat, "daily_life")

        cat, sub = map_osm_tags({"amenity": "bank"})
        self.assertEqual(cat, "daily_life")

        # Transport
        cat, sub = map_osm_tags({"highway": "bus_stop"})
        self.assertEqual(cat, "transport")

        cat, sub = map_osm_tags({"railway": "station"})
        self.assertEqual(cat, "transport")

        # Lifestyle
        cat, sub = map_osm_tags({"leisure": "park"})
        self.assertEqual(cat, "lifestyle")

        cat, sub = map_osm_tags({"amenity": "cafe"})
        self.assertEqual(cat, "lifestyle")

    def test_hyderabad_urban_validation(self):
        """Validates urban retrieval at Charminar, Hyderabad."""
        resp = self.client.get("/api/modules/places?lat=17.3616&lng=78.4747&radius_m=1500")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["module"], "places")
        self.assertIn(data["status"], ["available", "limited"])

        places = data["data"]["places"]
        self.assertGreaterEqual(len(places), 30)

        # Confirm strict distance sorting
        for i in range(len(places) - 1):
            self.assertLessEqual(places[i]["distance_m"], places[i + 1]["distance_m"])

        # Confirm all within radius
        for p in places:
            self.assertLessEqual(p["distance_m"], 1500.0)
            self.assertTrue(p["id"].startswith("osm_node_") or p["id"].startswith("osm_way_"))

        # Verify sample known landmarks in Old City
        names = [p["name"] for p in places]
        self.assertTrue(any("Charminar" in n or "Dawakhana" in n or "Hospital" in n for n in names))

    def test_warangal_town_validation(self):
        """Validates secondary town retrieval in Warangal / Hanamkonda."""
        resp = self.client.get("/api/modules/places?lat=17.9784&lng=79.5941&radius_m=1500")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        places = data["data"]["places"]
        self.assertGreaterEqual(len(places), 20)

        counts = data["data"]["counts_by_category"]
        self.assertGreater(counts.get("healthcare", 0), 0)
        self.assertGreater(counts.get("education", 0), 0)

    def test_alampur_rural_validation(self):
        """Validates rural border town retrieval at Alampur, Jogulamba Gadwal."""
        resp = self.client.get("/api/modules/places?lat=15.8778&lng=78.1311&radius_m=2000")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        places = data["data"]["places"]
        self.assertGreaterEqual(len(places), 1)

        # Check sample Alampur facilities
        names = [p["name"] for p in places]
        self.assertTrue(any("Alampur" in n or "Hospital" in n or "Bus" in n for n in names))

    def test_category_filtering(self):
        """Verifies category filtering restricts returned results accurately."""
        resp = self.client.get("/api/modules/places?lat=17.3616&lng=78.4747&radius_m=1500&categories=healthcare")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        places = data["data"]["places"]
        self.assertGreater(len(places), 0)
        for p in places:
            self.assertEqual(p["category"], "healthcare")

    def test_empty_results_handling(self):
        """Verifies honest empty state handling when no records exist within small radius in remote area."""
        # Query tiny 300m radius in a remote rural field (far from village centers)
        resp = self.client.get("/api/modules/places?lat=16.1000&lng=78.5000&radius_m=300")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(data["status"], ["unavailable", "limited"])
        if len(data["data"]["places"]) == 0:
            self.assertEqual(data["status"], "unavailable")
            self.assertIn("No facilities found", data["message"])
            self.assertIn("does not imply", " ".join(data["limitations"]))

    def test_rtree_rowid_alignment(self):
        """Verifies 100% 1:1 rowid alignment between osm_places and osm_places_rtree."""
        import sqlite3
        db_path = self.provider.db_path
        self.assertTrue(os.path.exists(db_path))
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Every entry in osm_places_rtree must map to a valid osm_places row
        cur.execute("SELECT COUNT(*) FROM osm_places_rtree r LEFT JOIN osm_places p ON p.rowid = r.id_int WHERE p.id IS NULL")
        orphans = cur.fetchone()[0]
        self.assertEqual(orphans, 0, "No orphaned R*Tree entries permitted")

        # Row counts must match exactly
        cur.execute("SELECT COUNT(*) FROM osm_places")
        places_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM osm_places_rtree")
        rtree_count = cur.fetchone()[0]
        self.assertEqual(places_count, rtree_count, "R*Tree count must equal osm_places count")
        conn.close()

    def test_deduplication_safety_preserves_distinct_stops(self):
        """Verifies that separate bus stops / amenities are not merged purely due to name proximity."""
        import sqlite3
        conn = sqlite3.connect(self.provider.db_path)
        cur = conn.cursor()
        # Find any bus stops with same name in same area
        cur.execute("""
            SELECT name, COUNT(*) as cnt
            FROM osm_places
            WHERE category = 'transport' AND subcategory = 'bus_stop' AND name != 'Unnamed place'
            GROUP BY name, ROUND(lat, 3), ROUND(lng, 3)
            HAVING cnt > 1
            LIMIT 5
        """)
        dups = cur.fetchall()
        conn.close()
        # If any opposite-direction stops exist in the dataset, they must have distinct OSM ids
        if dups:
            sample_name = dups[0][0]
            conn = sqlite3.connect(self.provider.db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, osm_type, osm_id, lat, lng FROM osm_places WHERE name = ?", (sample_name,))
            records = cur.fetchall()
            conn.close()
            osm_ids = [r[2] for r in records]
            self.assertEqual(len(osm_ids), len(set(osm_ids)), "Every distinct stop must retain unique OSM ID")

    def test_disentangled_total_found_and_display_cap(self):
        """Verifies that total_found and displayed_count accurately separate total results from the 100 cap."""
        # Query dense central Hyderabad with 3000m radius
        resp = self.client.get("/api/modules/places?lat=17.3616&lng=78.4747&radius_m=3000")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]

        places = data["places"]
        self.assertLessEqual(len(places), 100, "Displayed places must not exceed max_results (100)")
        self.assertIn("total_found", data)
        self.assertIn("displayed_count", data)
        if data["total_found"] > 100:
            self.assertTrue(data["cap_reached"])
            self.assertEqual(data["displayed_count"], len(places))
            self.assertGreater(data["total_found"], len(places))
            # Sum of counts_by_category should equal total_found
            category_sum = sum(data["counts_by_category"].values())
            self.assertEqual(category_sum, data["total_found"])

    def test_metadata_cache_invalidation_on_mtime(self):
        """Verifies that metadata cache updates when the underlying file mtime changes."""
        provider = TelanganaPlacesProvider()
        meta1 = provider.get_metadata()
        cached_mtime = provider._last_db_mtime
        self.assertIsNotNone(cached_mtime)

        # Force invalidation by resetting _last_db_mtime
        provider._last_db_mtime = None
        meta2 = provider.get_metadata()
        self.assertEqual(meta1["total_facilities"], meta2["total_facilities"])
        self.assertIsNotNone(provider._last_db_mtime)

    def test_evidence_builder_transparent_gaps_and_outages(self):
        """Verifies that EvidenceBuilder generates honest gaps for empty categories and provider outages."""
        from backend.app.schemas.base import ModuleResult, Coverage, DataSourceInfo
        from backend.app.schemas.location import PlacesData
        from backend.app.evidence.builder import EvidenceBuilder

        # Case 1: Provider outage (unavailable)
        outage_res = ModuleResult[PlacesData](
            module="places",
            status="unavailable",
            provenance_kind="map_listing",
            data=None,
            sources=[],
            coverage=Coverage(granularity="unknown", radius_m=1500, result_count=0),
            message="Database file missing"
        )
        items, gaps = EvidenceBuilder.build_evidence("loc_test", places_res=outage_res)
        self.assertTrue(any(g.module == "places" and "unavailable" in g.reason for g in gaps))

        # Case 2: Available with category gap (0 safety_infrastructure in radius)
        available_res = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(
                places=[],
                counts_by_category={
                    "healthcare": 2,
                    "education": 1,
                    "safety_infrastructure": 0,
                    "daily_life": 5,
                    "transport": 3,
                    "lifestyle": 4
                },
                radius_m=1500,
                cap_reached=False
            ),
            sources=[DataSourceInfo(name="OpenStreetMap")],
            coverage=Coverage(granularity="nearby_place", radius_m=1500, result_count=15),
            limitations=[]
        )
        items2, gaps2 = EvidenceBuilder.build_evidence("loc_test2", places_res=available_res)
        # safety_infrastructure count is 0 -> should record transparent gap explaining mapping gap
        safety_gap = next((g for g in gaps2 if g.module == "safety_infrastructure"), None)
        self.assertIsNotNone(safety_gap)
        self.assertIn("mapping data gap, not physical absence", safety_gap.reason)

    def test_telangana_places_provider_error_handling(self):
        """Verifies that TelanganaPlacesProvider returns an honest error result when database fails."""
        import tempfile
        # Create dummy provider pointing to non-existent db
        broken_provider = TelanganaPlacesProvider(db_path=os.path.join(tempfile.gettempdir(), "non_existent_telangana.db"))
        self.assertFalse(broken_provider.is_available())
        import asyncio
        res = asyncio.run(broken_provider.get_nearby_places(17.3616, 78.4747, 1500))
        self.assertEqual(res.status, "error")
        self.assertIn("not found", res.limitations[0].lower())

if __name__ == "__main__":
    unittest.main()
