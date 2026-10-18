import os
import math
import json
import sqlite3
import httpx
import logging
from datetime import datetime
from typing import Literal
from backend.app.providers.base import PlacesProvider, StoragePolicy
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.location import PlaceItem, PlacesData
from backend.app.utils.geo import haversine_distance_m
from backend.app.config import settings

logger = logging.getLogger(__name__)

class OverpassPlacesProvider(PlacesProvider):
    """
    OpenStreetMap Places Provider via Overpass API.
    Licensed under ODbL 1.0. Storage policy: storable.
    Used for reliable report snapshots and live exploration fallback.
    """
    MIRRORS = [
        "https://z.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    @property
    def name(self) -> str:
        return "OpenStreetMap (Overpass API)"

    @property
    def license(self) -> str:
        return "ODbL 1.0"

    @property
    def attribution_url(self) -> str:
        return "https://www.openstreetmap.org/copyright"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 60

    @property
    def capabilities(self) -> list[str]:
        return ["nearby_places", "amenities", "distance_ranking"]

    def _map_osm_to_category(self, tags: dict) -> tuple[Literal["healthcare", "education", "safety_infrastructure", "daily_life", "transport", "lifestyle"] | None, str | None]:
        amenity = tags.get("amenity", "")
        shop = tags.get("shop", "")
        leisure = tags.get("leisure", "")
        railway = tags.get("railway", "")
        highway = tags.get("highway", "")

        if amenity in ["hospital", "clinic", "pharmacy", "doctors", "dentist"]:
            return "healthcare", amenity
        if amenity in ["school", "college", "university", "kindergarten"]:
            return "education", amenity
        if amenity in ["police", "fire_station"]:
            return "safety_infrastructure", amenity
        if shop in ["supermarket", "convenience", "grocery", "chemist"] or amenity in ["bank", "atm", "fuel", "marketplace"]:
            return "daily_life", shop or amenity
        if railway in ["station", "subway_entrance", "halt"] or highway in ["bus_stop"] or amenity in ["bus_station"]:
            return "transport", railway or highway or amenity
        if leisure in ["park", "fitness_centre", "sports_centre", "playground"] or amenity in ["cafe", "restaurant", "fast_food", "community_centre"]:
            return "lifestyle", leisure or amenity
        return None, None

    async def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        categories: list[str] | None = None
    ) -> ModuleResult[PlacesData]:
        limit = self.max_results
        query = f"""[out:json][timeout:12];
(
  node["amenity"~"hospital|clinic|pharmacy|doctors|school|college|university|kindergarten|police|fire_station|bank|atm|fuel|bus_station|cafe|restaurant|community_centre"](around:{radius_m},{lat},{lng});
  node["shop"~"supermarket|convenience|grocery"](around:{radius_m},{lat},{lng});
  node["leisure"~"park|fitness_centre|sports_centre|playground"](around:{radius_m},{lat},{lng});
  node["railway"~"station|subway_entrance"](around:{radius_m},{lat},{lng});
  node["highway"="bus_stop"](around:{radius_m},{lat},{lng});
);
out center {limit};"""

        elements = []
        fetch_error = None

        headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}

        for mirror in self.MIRRORS:
            try:
                async with httpx.AsyncClient(timeout=14.0) as client:
                    resp = await client.post(mirror, data={"data": query}, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        elements = data.get("elements", [])
                        fetch_error = None
                        break
                    else:
                        fetch_error = f"HTTP {resp.status_code} from {mirror}"
            except Exception as e:
                fetch_error = f"{type(e).__name__} from {mirror}"
                continue

        source_info = self.get_data_source_info()

        if fetch_error and not elements:
            return ModuleResult[PlacesData](
                module="places",
                status="error",
                provenance_kind="map_listing",
                data=PlacesData(places=[], counts_by_category={}, radius_m=radius_m, cap_reached=False),
                sources=[source_info],
                coverage=Coverage(
                    granularity="nearby_place",
                    radius_m=radius_m,
                    result_count=0,
                    result_cap_reached=False,
                    note="OpenStreetMap Overpass servers temporarily timed out."
                ),
                fetched_at=datetime.utcnow(),
                limitations=[
                    "Public mirror latency or timeout occurred during exploration.",
                    "Map-data completeness varies by area; a lower count may reflect unmapped features."
                ],
                message=f"OpenStreetMap service temporarily busy: {fetch_error}"
            )

        places: list[PlaceItem] = []
        counts: dict[str, int] = {
            "healthcare": 0,
            "education": 0,
            "safety_infrastructure": 0,
            "daily_life": 0,
            "transport": 0,
            "lifestyle": 0
        }

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            p_lat = el.get("lat") or el.get("center", {}).get("lat")
            p_lng = el.get("lon") or el.get("center", {}).get("lon")
            if not p_lat or not p_lng:
                continue

            cat, subcat = self._map_osm_to_category(tags)
            if not cat:
                continue
            if categories and cat not in categories:
                continue

            dist = haversine_distance_m(lat, lng, p_lat, p_lng)
            if dist > radius_m:
                continue

            display_name = name or f"Unnamed {subcat or cat.replace('_', ' ').title()}"
            osm_id = f"osm_{el.get('type', 'node')}_{el.get('id')}"

            place_item = PlaceItem(
                id=osm_id,
                name=display_name,
                category=cat,
                subcategory=subcat,
                lat=p_lat,
                lng=p_lng,
                distance_m=dist,
                address=tags.get("addr:street") or tags.get("addr:full"),
                source_name=self.name,
                source_attribution=self.attribution_url
            )
            places.append(place_item)
            counts[cat] = counts.get(cat, 0) + 1

        # Sort places strictly by distance
        places.sort(key=lambda p: p.distance_m)

        cap_reached = len(elements) >= limit
        nearest_m = places[0].distance_m if places else None
        total_count = len(places)

        status: Literal["available", "limited", "unavailable", "error"] = "available"
        if total_count == 0:
            status = "unavailable"
        elif cap_reached or total_count < 3:
            status = "limited"

        limitations = [
            "Straight-line distances shown; actual walking or driving distance may be longer.",
            "Completeness depends on active OpenStreetMap community contributions."
        ]
        if cap_reached:
            limitations.append(f"Result limit reached ({limit} items). Reported counts are a lower bound (≥ {total_count}).")

        msg = None
        if status == "unavailable":
            msg = f"No amenities found within {radius_m}m in the OpenStreetMap database."

        return ModuleResult[PlacesData](
            module="places",
            status=status,
            provenance_kind="map_listing",
            data=PlacesData(
                places=places,
                counts_by_category=counts,
                radius_m=radius_m,
                cap_reached=cap_reached
            ),
            sources=[source_info],
            coverage=Coverage(
                granularity="nearby_place",
                radius_m=radius_m,
                result_count=total_count,
                result_cap_reached=cap_reached,
                nearest_distance_m=nearest_m,
                note=f"{total_count} places identified within {radius_m}m"
            ),
            fetched_at=datetime.utcnow(),
            limitations=limitations,
            message=msg
        )


class GooglePlacesProvider(PlacesProvider):
    """
    Google Places API Provider (live_only, subject to Google Terms of Service).
    Used for live interactive exploration when GOOGLE_MAPS_SERVER_KEY is configured.
    """
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_SERVER_KEY

    @property
    def name(self) -> str:
        return "Google Places"

    @property
    def license(self) -> str:
        return "Google Maps Platform Terms of Service"

    @property
    def attribution_url(self) -> str:
        return "https://cloud.google.com/maps-platform/terms"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "live_only"

    @property
    def max_results(self) -> int:
        return 60

    @property
    def capabilities(self) -> list[str]:
        return ["nearby_places", "ratings", "reviews_count"]

    async def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        categories: list[str] | None = None
    ) -> ModuleResult[PlacesData]:
        if not self.api_key:
            # Honest unconfigured state
            return ModuleResult[PlacesData](
                module="places",
                status="error",
                provenance_kind="map_listing",
                data=PlacesData(places=[], counts_by_category={}, radius_m=radius_m, cap_reached=False),
                sources=[self.get_data_source_info()],
                coverage=Coverage(granularity="nearby_place", radius_m=radius_m, result_count=0),
                fetched_at=datetime.utcnow(),
                limitations=["Google Maps Server Key is not configured."],
                message="Google Places API key is not configured in backend environment."
            )

        # Implementation for Google Places Nearby Search
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius_m,
            "key": self.api_key
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    places: list[PlaceItem] = []
                    counts: dict[str, int] = {
                        "healthcare": 0, "education": 0, "safety_infrastructure": 0,
                        "daily_life": 0, "transport": 0, "lifestyle": 0
                    }
                    for r in results:
                        p_loc = r.get("geometry", {}).get("location", {})
                        p_lat = p_loc.get("lat")
                        p_lng = p_loc.get("lng")
                        if p_lat is None or p_lng is None:
                            continue
                        dist = haversine_distance_m(lat, lng, p_lat, p_lng)
                        types = r.get("types", [])
                        
                        # Category mapping
                        cat: Literal["healthcare", "education", "safety_infrastructure", "daily_life", "transport", "lifestyle"] = "lifestyle"
                        if any(t in types for t in ["hospital", "doctor", "pharmacy", "health"]):
                            cat = "healthcare"
                        elif any(t in types for t in ["school", "university", "primary_school", "secondary_school"]):
                            cat = "education"
                        elif any(t in types for t in ["police", "fire_station"]):
                            cat = "safety_infrastructure"
                        elif any(t in types for t in ["supermarket", "grocery_or_supermarket", "bank", "atm", "gas_station"]):
                            cat = "daily_life"
                        elif any(t in types for t in ["subway_station", "transit_station", "bus_station", "train_station"]):
                            cat = "transport"

                        places.append(PlaceItem(
                            id=r.get("place_id", f"gp_{p_lat}_{p_lng}"),
                            name=r.get("name", "Unnamed place"),
                            category=cat,
                            subcategory=types[0] if types else None,
                            lat=p_lat,
                            lng=p_lng,
                            distance_m=dist,
                            address=r.get("vicinity"),
                            rating=r.get("rating"),
                            user_ratings_total=r.get("user_ratings_total"),
                            source_name=self.name,
                            source_attribution=self.attribution_url
                        ))
                        counts[cat] = counts.get(cat, 0) + 1

                    places.sort(key=lambda p: p.distance_m)
                    total = len(places)
                    nearest_m = places[0].distance_m if places else None

                    return ModuleResult[PlacesData](
                        module="places",
                        status="available" if total > 0 else "unavailable",
                        provenance_kind="map_listing",
                        data=PlacesData(places=places, counts_by_category=counts, radius_m=radius_m, cap_reached=False),
                        sources=[self.get_data_source_info()],
                        coverage=Coverage(
                            granularity="nearby_place",
                            radius_m=radius_m,
                            result_count=total,
                            nearest_distance_m=nearest_m
                        ),
                        fetched_at=datetime.utcnow(),
                        limitations=["Google Places listings are live and subject to search radius limits."]
                    )
        except Exception as e:
            logger.error(f"Google Places error: {e}")

        return ModuleResult[PlacesData](
            module="places",
            status="error",
            provenance_kind="map_listing",
            data=PlacesData(places=[], counts_by_category={}, radius_m=radius_m),
            sources=[self.get_data_source_info()],
            coverage=Coverage(granularity="nearby_place", radius_m=radius_m, result_count=0),
            fetched_at=datetime.utcnow(),
            limitations=["Google Places API encountered a network error."],
            message="Google Places request failed."
        )


class TelanganaPlacesProvider(PlacesProvider):
    """
    OpenStreetMap Statewide Places Provider for Telangana, India.
    Backed by local SQLite database with R*Tree spatial indexing.
    ODbL 1.0 licensed OpenStreetMap extract.
    """
    TELANGANA_BBOX = {
        "min_lat": 15.80,
        "max_lat": 19.92,
        "min_lng": 77.24,
        "max_lng": 81.35
    }

    def __init__(self, db_path: str | None = None):
        if db_path:
            self.db_path = db_path
        elif getattr(settings, "TELANGANA_PLACES_DB_PATH", None):
            self.db_path = os.path.abspath(settings.TELANGANA_PLACES_DB_PATH)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, "data", "telangana_places.db")
        self._metadata_cache: dict[str, str] | None = None
        self._last_db_mtime: float = 0.0

    @property
    def name(self) -> str:
        return "OpenStreetMap (Telangana Statewide Extract)"

    @property
    def license(self) -> str:
        return "ODbL 1.0"

    @property
    def attribution_url(self) -> str:
        return "https://www.openstreetmap.org/copyright"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 100

    @property
    def capabilities(self) -> list[str]:
        return ["nearby_places", "amenities", "distance_ranking", "statewide_offline", "instant_rtree"]

    def is_point_in_telangana(self, lat: float, lng: float) -> bool:
        """Determines if the coordinates fall within the Telangana state geographic envelope."""
        return (
            self.TELANGANA_BBOX["min_lat"] <= lat <= self.TELANGANA_BBOX["max_lat"] and
            self.TELANGANA_BBOX["min_lng"] <= lng <= self.TELANGANA_BBOX["max_lng"]
        )

    def is_available(self) -> bool:
        return os.path.exists(self.db_path)

    def get_metadata(self) -> dict[str, str]:
        # Check if database file modification time changed (auto-invalidation)
        try:
            current_mtime = os.path.getmtime(self.db_path) if self.is_available() else 0.0
            if current_mtime != self._last_db_mtime:
                self._metadata_cache = None
                self._last_db_mtime = current_mtime
        except Exception:
            pass

        if self._metadata_cache is not None:
            return self._metadata_cache
        if not self.is_available():
            return {}
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM dataset_metadata;")
            meta = dict(cursor.fetchall())
            conn.close()
            self._metadata_cache = meta
            return meta
        except Exception as e:
            logger.warning(f"Error reading dataset metadata: {e}")
            return {}

    def get_data_source_info(self) -> DataSourceInfo:
        meta = self.get_metadata()
        timestamp = meta.get("dataset_timestamp", "2026-10-15")
        return DataSourceInfo(
            name=self.name,
            license=self.license,
            attribution_url=self.attribution_url,
            storage_policy=self.storage_policy,
            description=f"Telangana-wide OpenStreetMap extract ({timestamp}) with local R*Tree spatial indexing."
        )

    async def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        categories: list[str] | None = None
    ) -> ModuleResult[PlacesData]:
        source_info = self.get_data_source_info()

        if not self.is_available():
            return ModuleResult[PlacesData](
                module="places",
                status="error",
                provenance_kind="map_listing",
                data=PlacesData(places=[], counts_by_category={}, radius_m=radius_m, cap_reached=False),
                sources=[source_info],
                coverage=Coverage(granularity="nearby_place", radius_m=radius_m, result_count=0),
                fetched_at=datetime.utcnow(),
                limitations=["Local Telangana places database is not found at configured path."],
                message="Telangana places database is not built. Please run preprocessing script."
            )

        # Delta calculation in degrees for R*Tree bounding box
        # Buffer bounding box by 25m to prevent IEEE 754 32-bit float truncation clipping at circular boundary
        buffered_radius_m = radius_m + 25
        delta_lat = buffered_radius_m / 111139.0
        cos_lat = math.cos(math.radians(lat))
        delta_lng = buffered_radius_m / (111139.0 * max(cos_lat, 0.01))

        min_lng = lng - delta_lng
        max_lng = lng + delta_lng
        min_lat = lat - delta_lat
        max_lat = lat + delta_lat

        all_matching_places: list[PlaceItem] = []
        counts: dict[str, int] = {
            "healthcare": 0,
            "education": 0,
            "safety_infrastructure": 0,
            "daily_life": 0,
            "transport": 0,
            "lifestyle": 0
        }

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Standard spatial intersection predicate for R*Tree
            query = """
                SELECT p.id, p.name, p.category, p.subcategory, p.lat, p.lng, p.address, p.osm_type, p.osm_id, p.tags_json
                FROM osm_places_rtree r
                JOIN osm_places p ON p.rowid = r.id_int
                WHERE r.max_lng >= ? AND r.min_lng <= ?
                  AND r.max_lat >= ? AND r.min_lat <= ?
            """
            cursor.execute(query, (min_lng, max_lng, min_lat, max_lat))
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                dist = haversine_distance_m(lat, lng, r["lat"], r["lng"])
                if dist > radius_m:
                    continue

                cat = r["category"]
                # Accumulate actual complete category counts for ALL facilities inside the survey radius
                counts[cat] = counts.get(cat, 0) + 1

                if categories and cat not in categories:
                    continue

                all_matching_places.append(PlaceItem(
                    id=r["id"],
                    name=r["name"],
                    category=cat,
                    subcategory=r["subcategory"],
                    lat=r["lat"],
                    lng=r["lng"],
                    distance_m=dist,
                    address=r["address"],
                    source_name=self.name,
                    source_attribution=self.attribution_url
                ))

        except Exception as e:
            logger.error(f"Error querying Telangana places database: {e}")
            return ModuleResult[PlacesData](
                module="places",
                status="error",
                provenance_kind="map_listing",
                data=PlacesData(places=[], counts_by_category={}, radius_m=radius_m, cap_reached=False),
                sources=[source_info],
                coverage=Coverage(granularity="nearby_place", radius_m=radius_m, result_count=0),
                fetched_at=datetime.utcnow(),
                limitations=[f"Database query error: {type(e).__name__}"],
                message="Failed to query local Telangana places database."
            )

        # Sort all matching places strictly by distance ascending
        all_matching_places.sort(key=lambda p: p.distance_m)

        total_found = len(all_matching_places)
        cap_reached = total_found > self.max_results
        displayed_places = all_matching_places[:self.max_results]
        displayed_count = len(displayed_places)
        nearest_m = displayed_places[0].distance_m if displayed_places else None

        meta = self.get_metadata()
        ds_time = meta.get("dataset_timestamp", "2026-10-15")

        status: Literal["available", "limited", "unavailable", "error"] = "available"
        if total_found == 0:
            status = "unavailable"
        elif cap_reached or total_found < 3:
            status = "limited"

        limitations = [
            "Straight-line distances shown; actual walking or driving distance may be longer.",
            f"Statewide OpenStreetMap extract snapshot: {ds_time}.",
            "Completeness varies by locality; in rural regions, absence of a record in OSM data does not imply the facility does not exist physically."
        ]
        if cap_reached:
            limitations.append(f"Result display limit reached: displaying {displayed_count} nearest of {total_found} total facilities identified within {radius_m}m.")

        msg = None
        if status == "unavailable":
            msg = f"No facilities found within {radius_m}m in OpenStreetMap records. (This indicates an absence of mapped records in the OSM dataset, not definitive proof of absence in the physical world)."

        coverage_note = (
            f"Displaying {displayed_count} nearest places ({total_found} total identified within {radius_m}m across Telangana dataset)"
            if cap_reached else
            f"{total_found} places identified within {radius_m}m across Telangana dataset"
        )

        return ModuleResult[PlacesData](
            module="places",
            status=status,
            provenance_kind="map_listing",
            data=PlacesData(
                places=displayed_places,
                counts_by_category=counts,
                radius_m=radius_m,
                cap_reached=cap_reached,
                total_found=total_found,
                displayed_count=displayed_count
            ),
            sources=[source_info],
            coverage=Coverage(
                granularity="nearby_place",
                radius_m=radius_m,
                result_count=total_found,
                result_cap_reached=cap_reached,
                nearest_distance_m=nearest_m,
                note=coverage_note
            ),
            fetched_at=datetime.utcnow(),
            limitations=limitations,
            message=msg
        )
