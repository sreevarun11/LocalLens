import httpx
import logging
from typing import Literal
from backend.app.providers.base import GeocodingProvider, StoragePolicy
from backend.app.schemas.location import AutocompletePrediction, LocationDetails
from backend.app.config import settings

logger = logging.getLogger(__name__)

class GoogleGeocodingProvider(GeocodingProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_SERVER_KEY

    @property
    def name(self) -> str:
        return "Google Maps Platform"

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
        return 5

    @property
    def capabilities(self) -> list[str]:
        return ["autocomplete", "details", "reverse_geocode"]

    async def autocomplete(self, query: str, session_token: str | None = None) -> list[AutocompletePrediction]:
        if not self.api_key:
            return []
        
        url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params = {
            "input": query,
            "key": self.api_key,
            "language": "en"
        }
        if session_token:
            params["sessiontoken"] = session_token
            
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    preds = []
                    for item in data.get("predictions", []):
                        struct = item.get("structured_formatting", {})
                        preds.append(AutocompletePrediction(
                            place_id=item.get("place_id"),
                            description=item.get("description", ""),
                            main_text=struct.get("main_text", item.get("description", "")),
                            secondary_text=struct.get("secondary_text"),
                            provider=self.name
                        ))
                    return preds
        except Exception as e:
            logger.error(f"Google autocomplete error: {e}")
        return []

    async def get_details(self, place_id: str, session_token: str | None = None) -> LocationDetails | None:
        if not self.api_key:
            return None
            
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "place_id,name,formatted_address,geometry,address_components",
            "key": self.api_key
        }
        if session_token:
            params["sessiontoken"] = session_token
            
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    result = resp.json().get("result", {})
                    loc = result.get("geometry", {}).get("location", {})
                    lat = loc.get("lat")
                    lng = loc.get("lng")
                    if lat is None or lng is None:
                        return None
                        
                    # Extract address components
                    locality, city, state, country, postal = None, None, None, None, None
                    for comp in result.get("address_components", []):
                        types = comp.get("types", [])
                        if "sublocality" in types or "neighborhood" in types:
                            locality = comp.get("long_name")
                        elif "locality" in types:
                            city = comp.get("long_name")
                        elif "administrative_area_level_1" in types:
                            state = comp.get("long_name")
                        elif "country" in types:
                            country = comp.get("long_name")
                        elif "postal_code" in types:
                            postal = comp.get("long_name")
                            
                    return LocationDetails(
                        place_id=place_id,
                        formatted_address=result.get("formatted_address", result.get("name", "")),
                        name=result.get("name", ""),
                        lat=lat,
                        lng=lng,
                        locality=locality,
                        city=city,
                        state=state,
                        country=country,
                        postal_code=postal,
                        provider=self.name
                    )
        except Exception as e:
            logger.error(f"Google place details error: {e}")
        return None

    async def reverse_geocode(self, lat: float, lng: float) -> LocationDetails | None:
        if not self.api_key:
            return None
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"latlng": f"{lat},{lng}", "key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        first = results[0]
                        return LocationDetails(
                            place_id=first.get("place_id", f"coords_{lat}_{lng}"),
                            formatted_address=first.get("formatted_address", f"{lat:.4f}, {lng:.4f}"),
                            name=first.get("formatted_address", "").split(",")[0],
                            lat=lat,
                            lng=lng,
                            provider=self.name
                        )
        except Exception as e:
            logger.error(f"Google reverse geocode error: {e}")
        return None


class PhotonGeocodingProvider(GeocodingProvider):
    """
    Fallback open geocoding provider based on Komoot Photon / OpenStreetMap.
    Used when Google API key is not configured or as secondary fallback.
    """
    @property
    def name(self) -> str:
        return "Photon (OpenStreetMap contributors)"

    @property
    def license(self) -> str:
        return "ODbL 1.0"

    @property
    def attribution_url(self) -> str:
        return "https://photon.komoot.io/"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 5

    @property
    def capabilities(self) -> list[str]:
        return ["autocomplete", "details", "reverse_geocode"]

    async def autocomplete(self, query: str, session_token: str | None = None) -> list[AutocompletePrediction]:
        url = "https://photon.komoot.io/api/"
        params = {"q": query, "limit": 5}
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    preds = []
                    for idx, feat in enumerate(data.get("features", [])):
                        props = feat.get("properties", {})
                        geom = feat.get("geometry", {})
                        coords = geom.get("coordinates", [])
                        lon = coords[0] if len(coords) >= 2 else None
                        lat = coords[1] if len(coords) >= 2 else None
                        
                        name = props.get("name", "Unknown location")
                        city = props.get("city") or props.get("state") or props.get("country", "")
                        osm_id = str(props.get("osm_id", idx))
                        desc_parts = [p for p in [name, props.get("district"), props.get("city"), props.get("state"), props.get("country")] if p]
                        desc = ", ".join(desc_parts)

                        if lat is not None and lon is not None:
                            place_id = f"photon_{lat:.6f}_{lon:.6f}_{osm_id}"
                        else:
                            place_id = f"photon_{osm_id}"

                        preds.append(AutocompletePrediction(
                            place_id=place_id,
                            description=desc,
                            main_text=name,
                            secondary_text=city,
                            provider=self.name
                        ))
                    return preds
        except Exception as e:
            logger.error(f"Photon autocomplete error: {e}")
        return []

    async def get_details(self, place_id: str, session_token: str | None = None) -> LocationDetails | None:
        # 1. If place_id has embedded coords: "photon_{lat}_{lng}_{osm_id}" or "coords_{lat}_{lng}"
        if place_id.startswith("photon_") or place_id.startswith("coords_"):
            parts = place_id.split("_")
            if len(parts) >= 3:
                try:
                    lat, lng = float(parts[1]), float(parts[2])
                    rev = await self.reverse_geocode(lat, lng)
                    if rev:
                        return rev
                    return LocationDetails(
                        place_id=place_id,
                        formatted_address=f"{lat:.4f}, {lng:.4f}",
                        name=f"{lat:.4f}, {lng:.4f}",
                        lat=lat,
                        lng=lng,
                        provider=self.name
                    )
                except Exception as e:
                    logger.error(f"Error parsing coordinates from place_id {place_id}: {e}")

        # 2. Fallback: treat place_id as search query or lookup via Photon API
        cleaned = place_id.replace("photon_", "").replace("coords_", "").strip()
        if cleaned:
            try:
                url = "https://photon.komoot.io/api/"
                params = {"q": cleaned, "limit": 1}
                async with httpx.AsyncClient(timeout=6.0) as client:
                    headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}
                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        features = data.get("features", [])
                        if features:
                            feat = features[0]
                            coords = feat.get("geometry", {}).get("coordinates", [])
                            if len(coords) >= 2:
                                lon, lat = coords[0], coords[1]
                                return await self.reverse_geocode(lat, lon)
            except Exception as e:
                logger.error(f"Photon get_details query fallback error: {e}")

        return None

    async def reverse_geocode(self, lat: float, lng: float) -> LocationDetails | None:
        url = "https://photon.komoot.io/reverse"
        params = {"lat": lat, "lon": lng}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    features = data.get("features", [])
                    if features:
                        props = features[0].get("properties", {})
                        name = props.get("name") or props.get("district") or props.get("city") or f"{lat:.4f}, {lng:.4f}"
                        desc_parts = [p for p in [name, props.get("district"), props.get("city"), props.get("state"), props.get("country")] if p]
                        desc = ", ".join(desc_parts)
                        return LocationDetails(
                            place_id=f"coords_{lat}_{lng}",
                            formatted_address=desc,
                            name=name,
                            lat=lat,
                            lng=lng,
                            locality=props.get("district") or props.get("locality"),
                            city=props.get("city"),
                            state=props.get("state"),
                            country=props.get("country"),
                            postal_code=props.get("postcode"),
                            provider=self.name
                        )
        except Exception as e:
            logger.error(f"Photon reverse geocode error: {e}")
        return LocationDetails(
            place_id=f"coords_{lat}_{lng}",
            formatted_address=f"{lat:.4f}, {lng:.4f}",
            name=f"{lat:.4f}, {lng:.4f}",
            lat=lat,
            lng=lng,
            provider=self.name
        )
