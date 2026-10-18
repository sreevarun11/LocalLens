"""
routing.py - Road-network routing and connectivity provider for LocalLens.

Integrates real road-network routing via OSRM (Open Source Routing Machine)
backed by OpenStreetMap road geometry.

Guarantees:
- Never substitutes straight-line calculations (e.g. haversine * 1.35) for a real road route.
- Never invents transit schedules, frequencies, or wait times without verified GTFS data.
- Never claims live traffic or real-time congestion predictions from free-flow road models.
- Returns explicit unavailable/error states when routes cannot be resolved.
"""

import logging
from datetime import datetime
from typing import Any, List, Optional

import httpx

from backend.app.config import settings
from backend.app.providers.base import RoutingProvider, StoragePolicy
from backend.app.schemas.base import Coverage, DataSourceInfo, ModuleResult
from backend.app.schemas.location import Coordinates
from backend.app.schemas.modules import CommuteData, CommuteModeResult

logger = logging.getLogger(__name__)


def validate_coordinates(coords: Coordinates) -> bool:
    """Validate latitude (-90 to 90) and longitude (-180 to 180)."""
    if coords is None:
        return False
    if not isinstance(coords.lat, (int, float)) or not isinstance(coords.lng, (int, float)):
        return False
    if not (-90.0 <= coords.lat <= 90.0 and -180.0 <= coords.lng <= 180.0):
        return False
    return True


class OSRMRouteProvider(RoutingProvider):
    """
    Road-network routing provider using Open Source Routing Machine (OSRM)
    backed by OpenStreetMap data.
    """

    def __init__(self, base_url: Optional[str] = None, timeout_s: float = 8.0):
        self.base_url = (base_url or getattr(settings, "OSRM_BASE_URL", "http://router.project-osrm.org")).rstrip("/")
        self.timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "OSRM Road-Network Engine (OpenStreetMap)"

    @property
    def license(self) -> str:
        return "Open Database License (ODbL) / OpenStreetMap contributors"

    @property
    def attribution_url(self) -> str:
        return "https://www.openstreetmap.org/copyright"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "live_only"

    @property
    def max_results(self) -> int:
        return 4

    @property
    def capabilities(self) -> List[str]:
        return ["driving", "walking"]

    async def get_commute(
        self,
        origin: Coordinates,
        destination_coords: Coordinates,
        destination_name: str,
        departure_time: Optional[str] = None
    ) -> ModuleResult[CommuteData]:
        source_info = self.get_data_source_info()
        now = datetime.utcnow()

        # 1. Validate coordinates
        if not validate_coordinates(origin) or not validate_coordinates(destination_coords):
            return ModuleResult[CommuteData](
                module="commute",
                status="error",
                provenance_kind="derived",
                message="Invalid geographic coordinates provided (latitudes must be between -90 and 90, longitudes between -180 and 180).",
                data=CommuteData(
                    origin_coords=origin,
                    destination_name=destination_name,
                    destination_coords=destination_coords,
                    modes={},
                    traffic_claim="Routing request rejected due to invalid coordinates."
                ),
                sources=[source_info],
                coverage=Coverage(granularity="exact_place"),
                fetched_at=now,
                limitations=["Coordinates must fall within valid global latitude/longitude bounds."]
            )

        # 2. Check identical origin and destination
        if origin.lat == destination_coords.lat and origin.lng == destination_coords.lng:
            modes = {
                "driving": CommuteModeResult(
                    mode="driving",
                    duration_min=0,
                    duration_s=0.0,
                    distance_km=0.0,
                    distance_m=0.0,
                    status="available",
                    route_summary="Origin and destination are identical",
                    route_geometry=[[origin.lng, origin.lat]],
                    provider=self.name,
                    data_kind="road_network_estimate",
                    limitations=["Origin and destination are identical."]
                ),
                "walking": CommuteModeResult(
                    mode="walking",
                    duration_min=0,
                    duration_s=0.0,
                    distance_km=0.0,
                    distance_m=0.0,
                    status="available",
                    route_summary="Origin and destination are identical",
                    route_geometry=[[origin.lng, origin.lat]],
                    provider=self.name,
                    data_kind="road_network_estimate",
                    limitations=["Origin and destination are identical."]
                ),
                "transit": CommuteModeResult(
                    mode="transit",
                    status="unavailable",
                    route_summary="Public transit timetables unavailable without a verified GTFS feed",
                    provider="LocalLens Transit Registry",
                    data_kind="unavailable",
                    limitations=["Public transit timetables require an official GTFS feed."]
                )
            }
            return ModuleResult[CommuteData](
                module="commute",
                status="available",
                provenance_kind="derived",
                data=CommuteData(
                    origin_coords=origin,
                    destination_name=destination_name,
                    destination_coords=destination_coords,
                    modes=modes,
                    traffic_claim="Zero distance between identical coordinates."
                ),
                sources=[source_info],
                coverage=Coverage(granularity="exact_place"),
                fetched_at=now,
                limitations=["Zero distance between identical coordinates."]
            )

        # 3. Query OSRM Driving Route
        # Format: /route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson
        url = f"{self.base_url}/route/v1/driving/{origin.lng},{origin.lat};{destination_coords.lng},{destination_coords.lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.get(url, params=params)

                if resp.status_code != 200:
                    logger.warning(f"OSRM returned HTTP {resp.status_code} for {origin} -> {destination_coords}")
                    return ModuleResult[CommuteData](
                        module="commute",
                        status="error",
                        provenance_kind="derived",
                        message=f"OSRM routing provider returned HTTP {resp.status_code}.",
                        data=CommuteData(
                            origin_coords=origin,
                            destination_name=destination_name,
                            destination_coords=destination_coords,
                            modes={},
                            traffic_claim="Routing unavailable due to upstream provider error."
                        ),
                        sources=[source_info],
                        coverage=Coverage(granularity="exact_place"),
                        fetched_at=now,
                        limitations=[
                            "OSRM demo service returned an error. Service availability is not guaranteed.",
                            "Do not substitute straight-line distances as road routes."
                        ]
                    )

                data = resp.json()

        except httpx.TimeoutException:
            logger.warning(f"OSRM routing timed out after {self.timeout_s}s for {origin} -> {destination_coords}")
            return ModuleResult[CommuteData](
                module="commute",
                status="error",
                provenance_kind="derived",
                message=f"Road-network routing request timed out after {self.timeout_s}s. Upstream OSRM service may be experiencing high load.",
                data=CommuteData(
                    origin_coords=origin,
                    destination_name=destination_name,
                    destination_coords=destination_coords,
                    modes={},
                    traffic_claim="Routing request timed out."
                ),
                sources=[source_info],
                coverage=Coverage(granularity="exact_place"),
                fetched_at=now,
                limitations=[
                    "Public OSRM demo server is a development dependency with no production SLA.",
                    "Timeouts indicate upstream queueing or connectivity latency."
                ]
            )
        except Exception as e:
            logger.error(f"OSRM request failed: {e}")
            return ModuleResult[CommuteData](
                module="commute",
                status="error",
                provenance_kind="derived",
                message=f"Road-network routing provider unreachable: {str(e)}",
                data=CommuteData(
                    origin_coords=origin,
                    destination_name=destination_name,
                    destination_coords=destination_coords,
                    modes={},
                    traffic_claim="Routing service unreachable."
                ),
                sources=[source_info],
                coverage=Coverage(granularity="exact_place"),
                fetched_at=now,
                limitations=["Network error connecting to OSRM road-network engine."]
            )

        # 4. Parse OSRM Response
        code = data.get("code")
        routes = data.get("routes", [])

        modes: dict[str, CommuteModeResult] = {}

        if code == "Ok" and routes:
            primary_route = routes[0]
            dist_m = float(primary_route.get("distance", 0.0))
            dur_s = float(primary_route.get("duration", 0.0))
            dist_km = round(dist_m / 1000.0, 1)
            dur_min = max(1, int(round(dur_s / 60.0)))
            geometry = primary_route.get("geometry", {}).get("coordinates", [])

            modes["driving"] = CommuteModeResult(
                mode="driving",
                duration_min=dur_min,
                duration_s=dur_s,
                distance_km=dist_km,
                distance_m=dist_m,
                status="available",
                route_summary=f"Via mapped road network (~{dist_km} km)",
                route_geometry=geometry,
                provider=self.name,
                data_kind="road_network_estimate",
                limitations=[
                    "Estimated driving duration is derived from OpenStreetMap road geometry and posted speed limits under nominal, free-flow conditions.",
                    "Real-time traffic congestion, signal delays, construction bottlenecks, and weather conditions are NOT factored.",
                    "Public OSRM demo service is a development dependency, not a commercial live-traffic provider."
                ]
            )

            # Walking evaluation based on actual road distance
            if dist_km <= 4.0:
                # Approximate pedestrian pace (4.5 km/h) along road network geometry
                walk_dur_min = int(round((dist_km / 4.5) * 60.0))
                modes["walking"] = CommuteModeResult(
                    mode="walking",
                    duration_min=walk_dur_min,
                    duration_s=walk_dur_min * 60.0,
                    distance_km=dist_km,
                    distance_m=dist_m,
                    status="available",
                    route_summary=f"Pedestrian road route (~{dist_km} km)",
                    route_geometry=geometry,
                    provider=self.name,
                    data_kind="road_network_estimate",
                    limitations=[
                        "Pedestrian duration is estimated at 4.5 km/h along mapped road geometry.",
                        "Sidewalk availability, pedestrian crossings, and terrain gradients are not verified."
                    ]
                )
            else:
                modes["walking"] = CommuteModeResult(
                    mode="walking",
                    distance_km=dist_km,
                    distance_m=dist_m,
                    status="unavailable",
                    route_summary=f"Distance ({dist_km} km) exceeds practical walking range (> 4 km)",
                    provider=self.name,
                    data_kind="unavailable",
                    limitations=["Walking route exceeds standard pedestrian distance threshold (4 km)."]
                )

        else:
            # Code is NoRoute, NoSegment, or empty
            reason = "No continuous road route found between coordinates." if code == "NoRoute" else f"OSRM status: {code}"
            modes["driving"] = CommuteModeResult(
                mode="driving",
                status="unavailable",
                route_summary=reason,
                provider=self.name,
                data_kind="unavailable",
                limitations=["No navigable road network found connecting the specified coordinates."]
            )
            modes["walking"] = CommuteModeResult(
                mode="walking",
                status="unavailable",
                route_summary=reason,
                provider=self.name,
                data_kind="unavailable",
                limitations=["No pedestrian road network found connecting the specified coordinates."]
            )

        # 5. Public Transit Honesty
        # We do NOT invent bus/metro schedules or travel times without a verified GTFS feed.
        modes["transit"] = CommuteModeResult(
            mode="transit",
            status="unavailable",
            route_summary="Public transit timetables, route schedules, and journey times are unavailable without an official GTFS feed.",
            provider="LocalLens Transit Registry",
            data_kind="unavailable",
            limitations=[
                "Public transit timetables, route frequencies, and actual journey times require an official agency GTFS feed.",
                "Estimated transit times are not invented or synthesized from car speeds."
            ]
        )

        overall_status = "available" if any(m.status == "available" for m in modes.values()) else "unavailable"

        return ModuleResult[CommuteData](
            module="commute",
            status=overall_status,
            provenance_kind="derived",
            data=CommuteData(
                origin_coords=origin,
                destination_name=destination_name,
                destination_coords=destination_coords,
                modes=modes,
                traffic_claim="Nominal road-network routing estimate under standard road speeds. Live traffic conditions, signal delays, and temporary congestion are not factored."
            ),
            sources=[source_info],
            coverage=Coverage(granularity="exact_place"),
            fetched_at=now,
            limitations=[
                "Road-network routing estimates reflect OpenStreetMap road geometry and posted speeds under free-flow conditions; live traffic is NOT factored.",
                "Public transit route schedules and timetables are unavailable without an official agency GTFS feed.",
                "Public OSRM demo server is for development use and is not an enterprise-guaranteed production SLA."
            ]
        )


class GoogleRoutesProvider(RoutingProvider):
    """
    Google Routes API provider.
    When GOOGLE_MAPS_SERVER_KEY is not configured, delegates to OSRMRouteProvider
    instead of calculating synthetic multipliers or fake travel speeds.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GOOGLE_MAPS_SERVER_KEY", None)
        self.osrm_fallback = OSRMRouteProvider()

    @property
    def name(self) -> str:
        return "Google Routes API" if self.api_key else self.osrm_fallback.name

    @property
    def license(self) -> str:
        return "Google Maps Platform Terms of Service" if self.api_key else self.osrm_fallback.license

    @property
    def attribution_url(self) -> str:
        return "https://cloud.google.com/maps-platform/terms" if self.api_key else self.osrm_fallback.attribution_url

    @property
    def storage_policy(self) -> StoragePolicy:
        return "live_only"

    @property
    def max_results(self) -> int:
        return 4

    @property
    def capabilities(self) -> List[str]:
        return ["driving", "transit", "walking"] if self.api_key else self.osrm_fallback.capabilities

    async def get_commute(
        self,
        origin: Coordinates,
        destination_coords: Coordinates,
        destination_name: str,
        departure_time: Optional[str] = None
    ) -> ModuleResult[CommuteData]:
        # If API key is not configured, delegate directly to real OSRM road-network routing.
        # NEVER compute synthetic distance multipliers or invented travel speeds!
        if not self.api_key:
            return await self.osrm_fallback.get_commute(
                origin=origin,
                destination_coords=destination_coords,
                destination_name=destination_name,
                departure_time=departure_time
            )

        # Real Google Routes API call when key is explicitly set
        source_info = self.get_data_source_info()
        modes_result: dict[str, CommuteModeResult] = {}

        for mode in ["DRIVE", "TRANSIT", "WALK"]:
            url = "https://routes.googleapis.com/directions/v2:computeRoutes"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.description"
            }
            body = {
                "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lng}}},
                "destination": {"location": {"latLng": {"latitude": destination_coords.lat, "longitude": destination_coords.lng}}},
                "travelMode": mode
            }
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(url, json=body, headers=headers)
                    if resp.status_code == 200:
                        r_data = resp.json()
                        routes = r_data.get("routes", [])
                        m_key = "driving" if mode == "DRIVE" else ("transit" if mode == "TRANSIT" else "walking")
                        if routes:
                            first = routes[0]
                            dur_str = str(first.get("duration", "0s")).replace("s", "")
                            dur_s = float(dur_str) if dur_str.replace(".", "", 1).isdigit() else None
                            dur_min = int(round(dur_s / 60.0)) if dur_s is not None else None
                            dist_m = float(first.get("distanceMeters", 0))
                            dist_km = round(dist_m / 1000.0, 1)
                            modes_result[m_key] = CommuteModeResult(
                                mode=m_key,  # type: ignore
                                duration_min=dur_min,
                                duration_s=dur_s,
                                distance_km=dist_km,
                                distance_m=dist_m,
                                status="available",
                                route_summary=first.get("description", f"{dist_km} km"),
                                provider=self.name,
                                data_kind="live_traffic" if mode == "DRIVE" else "timetable_schedule",
                                limitations=["Google Routes API live estimate."]
                            )
                        else:
                            modes_result[m_key] = CommuteModeResult(
                                mode=m_key,  # type: ignore
                                status="unavailable",
                                route_summary=f"{m_key.title()} route unavailable",
                                provider=self.name,
                                data_kind="unavailable",
                                limitations=[f"No {m_key} route returned by Google Routes."]
                            )
            except Exception as e:
                logger.error(f"Google Routes error for {mode}: {e}")

        return ModuleResult[CommuteData](
            module="commute",
            status="available" if any(m.status == "available" for m in modes_result.values()) else "unavailable",
            provenance_kind="derived",
            data=CommuteData(
                origin_coords=origin,
                destination_name=destination_name,
                destination_coords=destination_coords,
                modes=modes_result,
                traffic_claim="Google Routes API calculation."
            ),
            sources=[source_info],
            coverage=Coverage(granularity="exact_place"),
            fetched_at=datetime.utcnow(),
            limitations=[
                "Live traffic times vary based on actual departure time and congestion.",
                "Public transit availability depends on agency schedules."
            ]
        )
