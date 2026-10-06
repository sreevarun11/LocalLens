import httpx
import logging
from datetime import datetime
from backend.app.providers.base import RoutingProvider, StoragePolicy
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.location import Coordinates
from backend.app.schemas.modules import CommuteData, CommuteModeResult
from backend.app.utils.geo import haversine_distance_m
from backend.app.config import settings

logger = logging.getLogger(__name__)

class GoogleRoutesProvider(RoutingProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_SERVER_KEY

    @property
    def name(self) -> str:
        return "Google Routes API"

    @property
    def license(self) -> str:
        return "Google Maps Platform Terms of Service"

    @property
    def attribution_url(self) -> str:
        return "https://cloud.google.com/maps-platform/terms"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "live_only"  # Routes results must NEVER be cached or persisted

    @property
    def max_results(self) -> int:
        return 4

    @property
    def capabilities(self) -> list[str]:
        return ["driving", "transit", "walking", "two_wheeler"]

    async def get_commute(
        self,
        origin: Coordinates,
        destination_coords: Coordinates,
        destination_name: str,
        departure_time: str | None = None
    ) -> ModuleResult[CommuteData]:
        source_info = self.get_data_source_info()

        if not self.api_key:
            # Fallback estimation based on road-factor distance when key is not configured
            straight_m = haversine_distance_m(origin.lat, origin.lng, destination_coords.lat, destination_coords.lng)
            road_km = round((straight_m * 1.35) / 1000.0, 1)
            
            # Modeled estimates: 25 km/h driving in urban traffic, 15 km/h transit, 4.5 km/h walking
            drive_min = max(5, int(round((road_km / 25.0) * 60)))
            transit_min = max(10, int(round((road_km / 16.0) * 60 + 8))) # includes wait time
            walk_min = int(round((road_km / 4.5) * 60))

            modes = {
                "driving": CommuteModeResult(
                    mode="driving",
                    duration_min=drive_min,
                    distance_km=road_km,
                    status="available",
                    route_summary=f"Via arterial roads (~{road_km} km)",
                    provider="Estimated (Urban Traffic Baseline)"
                ),
                "transit": CommuteModeResult(
                    mode="transit",
                    duration_min=transit_min,
                    distance_km=road_km,
                    status="available",
                    route_summary="Bus / Metro network estimate",
                    provider="Estimated (Urban Transit Baseline)"
                ),
                "walking": CommuteModeResult(
                    mode="walking",
                    duration_min=walk_min if walk_min <= 120 else None,
                    distance_km=road_km,
                    status="available" if walk_min <= 120 else "unavailable",
                    route_summary=f"Pedestrian route (~{road_km} km)" if walk_min <= 120 else "Exceeds standard walking distance",
                    provider="Estimated"
                )
            }

            return ModuleResult[CommuteData](
                module="commute",
                status="limited",
                provenance_kind="modeled_estimate",
                data=CommuteData(
                    destination_name=destination_name,
                    destination_coords=destination_coords,
                    modes=modes
                ),
                sources=[DataSourceInfo(
                    name="LocalLens Urban Commute Model",
                    license="Derived Estimate",
                    attribution="Modeled from road-network factor and peak urban speeds"
                )],
                coverage=Coverage(
                    granularity="exact_place",
                    note="Modeled estimate. Configure GOOGLE_MAPS_SERVER_KEY for live traffic and multi-modal transit schedules."
                ),
                fetched_at=datetime.utcnow(),
                limitations=[
                    "Modeled estimate based on typical city traffic speeds — live traffic conditions not factored.",
                    "Travel times vary widely by time of day, weather, and construction."
                ]
            )

        # Real Google Routes call when key is set
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
                            dur_str = first.get("duration", "0s").replace("s", "")
                            dur_min = int(float(dur_str) / 60.0) if dur_str.isdigit() else None
                            dist_m = first.get("distanceMeters", 0)
                            dist_km = round(dist_m / 1000.0, 1)
                            modes_result[m_key] = CommuteModeResult(
                                mode=m_key,
                                duration_min=dur_min,
                                distance_km=dist_km,
                                status="available",
                                route_summary=first.get("description", f"{dist_km} km"),
                                provider=self.name
                            )
                        else:
                            modes_result[m_key] = CommuteModeResult(
                                mode=m_key,
                                status="unavailable",
                                route_summary=f"{m_key.title()} route unavailable",
                                provider=self.name
                            )
            except Exception as e:
                logger.error(f"Google Routes error for {mode}: {e}")

        return ModuleResult[CommuteData](
            module="commute",
            status="available" if any(m.status == "available" for m in modes_result.values()) else "unavailable",
            provenance_kind="derived",
            data=CommuteData(
                destination_name=destination_name,
                destination_coords=destination_coords,
                modes=modes_result
            ),
            sources=[source_info],
            coverage=Coverage(granularity="exact_place"),
            fetched_at=datetime.utcnow(),
            limitations=[
                "Live traffic times vary based on actual departure time and congestion.",
                "Public transit availability depends on agency schedules."
            ]
        )
