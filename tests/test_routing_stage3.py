import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx

from backend.app.evidence.builder import EvidenceBuilder
from backend.app.main import app
from backend.app.providers.routing import GoogleRoutesProvider, OSRMRouteProvider, validate_coordinates
from backend.app.schemas.base import Coverage, DataSourceInfo, ModuleResult
from backend.app.schemas.location import Coordinates
from backend.app.schemas.modules import CommuteData, CommuteModeResult, CommuteRequest


class TestRoutingStage3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.osrm = OSRMRouteProvider()

    def test_coordinate_validation(self):
        """Verify strict coordinate boundary validation."""
        valid_coords = Coordinates(lat=17.4401, lng=78.3489)
        self.assertTrue(validate_coordinates(valid_coords))

        invalid_lat_high = Coordinates(lat=91.0, lng=78.3489)
        self.assertFalse(validate_coordinates(invalid_lat_high))

        invalid_lat_low = Coordinates(lat=-90.5, lng=78.3489)
        self.assertFalse(validate_coordinates(invalid_lat_low))

        invalid_lng_high = Coordinates(lat=17.4401, lng=180.5)
        self.assertFalse(validate_coordinates(invalid_lng_high))

        invalid_lng_low = Coordinates(lat=17.4401, lng=-181.0)
        self.assertFalse(validate_coordinates(invalid_lng_low))

        # Test provider rejection on invalid coordinates
        res = asyncio.run(self.osrm.get_commute(
            origin=invalid_lat_high,
            destination_coords=valid_coords,
            destination_name="Test"
        ))
        self.assertEqual(res.status, "error")
        self.assertIn("Invalid geographic coordinates", res.message)

    def test_identical_origin_and_destination(self):
        """Verify identical origin and destination returns 0km and 0min immediately."""
        origin = Coordinates(lat=17.4401, lng=78.3489)
        dest = Coordinates(lat=17.4401, lng=78.3489)

        res = asyncio.run(self.osrm.get_commute(origin, dest, "Same Point"))
        self.assertEqual(res.status, "available")
        self.assertIsNotNone(res.data)
        driving = res.data.modes["driving"]
        self.assertEqual(driving.distance_km, 0.0)
        self.assertEqual(driving.duration_min, 0)
        self.assertEqual(driving.status, "available")

    def test_osrm_valid_route_live(self):
        """Test real road-network routing between Gachibowli and HITEC City via public OSRM."""
        origin = Coordinates(lat=17.4401, lng=78.3489)  # Gachibowli
        dest = Coordinates(lat=17.4435, lng=78.3772)    # HITEC City

        try:
            res = asyncio.run(self.osrm.get_commute(origin, dest, "HITEC City"))
        except Exception as e:
            self.skipTest(f"OSRM demo service unreachable in this environment: {e}")

        # If public OSRM is accessible
        if res.status == "available":
            self.assertIsNotNone(res.data)
            driving = res.data.modes.get("driving")
            self.assertIsNotNone(driving)
            self.assertEqual(driving.status, "available")
            self.assertGreater(driving.distance_km, 3.0)
            self.assertLess(driving.distance_km, 12.0)
            self.assertGreater(driving.duration_min, 2)
            self.assertIsNotNone(driving.route_geometry)
            self.assertGreater(len(driving.route_geometry), 10)
            self.assertEqual(driving.data_kind, "road_network_estimate")
            self.assertIn("OSRM", driving.provider)

            # Public transit schedule honesty
            transit = res.data.modes.get("transit")
            self.assertIsNotNone(transit)
            self.assertEqual(transit.status, "unavailable")
            self.assertIsNone(transit.duration_min)
            self.assertIn("GTFS", transit.route_summary)

            # Absence of misleading live traffic claims
            self.assertIn("nominal", res.data.traffic_claim.lower())
            self.assertIn("not factored", res.data.traffic_claim.lower())

    def test_provider_timeout_handling(self):
        """Verify OSRM timeouts return graceful error status without crashing."""
        slow_osrm = OSRMRouteProvider(timeout_s=0.000001)
        origin = Coordinates(lat=17.4401, lng=78.3489)
        dest = Coordinates(lat=17.4435, lng=78.3772)

        res = asyncio.run(slow_osrm.get_commute(origin, dest, "HITEC City"))
        self.assertEqual(res.status, "error")
        self.assertIn("timed out", res.message.lower())
        self.assertEqual(res.data.traffic_claim, "Routing request timed out.")

    def test_malformed_response_handling(self):
        """Verify non-200 and malformed responses are handled safely."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 502
            mock_get.return_value = mock_resp

            origin = Coordinates(lat=17.4401, lng=78.3489)
            dest = Coordinates(lat=17.4435, lng=78.3772)

            res = asyncio.run(self.osrm.get_commute(origin, dest, "Test"))
            self.assertEqual(res.status, "error")
            self.assertIn("HTTP 502", res.message)

    def test_no_route_handling(self):
        """Verify OSRM NoRoute code returns unavailable state."""
        from unittest.mock import MagicMock
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "code": "NoRoute",
                "routes": []
            }
            mock_get.return_value = mock_resp

            origin = Coordinates(lat=17.4401, lng=78.3489)
            dest = Coordinates(lat=17.4435, lng=78.3772)

            res = asyncio.run(self.osrm.get_commute(origin, dest, "Isolated Island"))
            self.assertEqual(res.status, "unavailable")
            self.assertEqual(res.data.modes["driving"].status, "unavailable")
            self.assertIn("No continuous road route found", res.data.modes["driving"].route_summary)

    def test_google_routes_fallback_no_synthetic_math(self):
        """Verify GoogleRoutesProvider without API key delegates to OSRM without synthetic math."""
        provider = GoogleRoutesProvider(api_key=None)
        self.assertIn("OSRM", provider.name)
        self.assertIn("OpenStreetMap", provider.license)

        origin = Coordinates(lat=17.4401, lng=78.3489)
        dest = Coordinates(lat=17.4401, lng=78.3489)

        res = asyncio.run(provider.get_commute(origin, dest, "Same"))
        self.assertEqual(res.status, "available")
        self.assertEqual(res.data.modes["driving"].distance_km, 0.0)

    def test_commute_api_endpoint(self):
        """Verify the POST /api/modules/commute endpoint."""
        # 1. Missing coordinates returns 400
        resp_bad = self.client.post("/api/modules/commute", json={
            "origin": {"lat": 17.4401, "lng": 78.3489}
        })
        self.assertEqual(resp_bad.status_code, 400)

        # 2. Valid request
        payload = {
            "origin": {"lat": 17.4401, "lng": 78.3489},
            "destination_coords": {"lat": 17.4401, "lng": 78.3489},
            "destination_query": "Same Point"
        }
        resp = self.client.post("/api/modules/commute", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "available")
        self.assertIn("modes", data["data"])
        self.assertIn("driving", data["data"]["modes"])
        # Check nearby transit facilities enrichment in Telangana
        self.assertIn("nearby_transit_nodes_count", data["data"])

    def test_evidence_builder_commute_and_transit_gap(self):
        """Verify evidence builder records commute items and transparent public transit gap."""
        commute_res = ModuleResult[CommuteData](
            module="commute",
            status="available",
            provenance_kind="derived",
            data=CommuteData(
                destination_name="Secunderabad",
                destination_coords=Coordinates(lat=17.4334, lng=78.5015),
                modes={
                    "driving": CommuteModeResult(
                        mode="driving",
                        duration_min=32,
                        distance_km=18.5,
                        status="available",
                        provider="OSRM Road-Network Engine",
                        data_kind="road_network_estimate"
                    ),
                    "transit": CommuteModeResult(
                        mode="transit",
                        status="unavailable",
                        route_summary="Public transit timetables unavailable without an official GTFS feed.",
                        provider="LocalLens Transit Registry",
                        data_kind="unavailable"
                    )
                }
            ),
            sources=[DataSourceInfo(name="OSRM Road-Network Engine")],
            coverage=Coverage(granularity="exact_place")
        )

        items, gaps = EvidenceBuilder.build_evidence(
            locality_key="loc_test",
            commute_res=commute_res
        )

        # 1. Check commute evidence items
        drive_dur = next((it for it in items if it.module == "commute" and it.metric == "driving_duration_min"), None)
        self.assertIsNotNone(drive_dur)
        self.assertEqual(drive_dur.value, 32)

        drive_dist = next((it for it in items if it.module == "commute" and it.metric == "driving_distance_km"), None)
        self.assertIsNotNone(drive_dist)
        self.assertEqual(drive_dist.value, 18.5)

        # 2. Check transit gap is recorded honestly
        transit_gap = next((g for g in gaps if g.module == "commute" and "GTFS" in g.reason), None)
        self.assertIsNotNone(transit_gap)
        self.assertIn("transit times are not invented", transit_gap.reason)


if __name__ == "__main__":
    unittest.main()
