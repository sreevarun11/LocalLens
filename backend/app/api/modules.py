from fastapi import APIRouter, Query, HTTPException
from backend.app.schemas.base import ModuleResult, Coverage
from backend.app.schemas.location import PlacesData, Coordinates
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, SafetyAndCrimeData, CommuteData, CommuteRequest
from backend.app.providers.places import OverpassPlacesProvider, GooglePlacesProvider, TelanganaPlacesProvider
from backend.app.providers.environment import (
    OpenMeteoAirQualityProvider,
    OpenAQAirQualityProvider,
    DefaultWaterQualityProvider,
    DefaultCrimeProvider
)
from backend.app.providers.safety import TelanganaSafetyProvider
from backend.app.providers.routing import GoogleRoutesProvider, OSRMRouteProvider
from backend.app.config import settings

router = APIRouter(prefix="/modules", tags=["Modules"])

telangana_places = TelanganaPlacesProvider()
overpass_places = OverpassPlacesProvider()
google_places = GooglePlacesProvider()
open_meteo_aq = OpenMeteoAirQualityProvider()
openaq_aq = OpenAQAirQualityProvider()
water_provider = DefaultWaterQualityProvider()
crime_provider = DefaultCrimeProvider()
safety_provider = TelanganaSafetyProvider()
routes_provider = GoogleRoutesProvider() if settings.GOOGLE_MAPS_SERVER_KEY else OSRMRouteProvider()

@router.get("/places", response_model=ModuleResult[PlacesData])
async def get_places(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    radius_m: int = Query(1500, ge=300, le=5000),
    categories: list[str] | None = Query(None)
):
    # If Google Maps server key is set, try live Google Places
    if settings.GOOGLE_MAPS_SERVER_KEY:
        res = await google_places.get_nearby_places(lat, lng, radius_m, categories)
        if res.status != "error":
            return res

    # 1. Primary provider for Telangana state searches: Local indexed SQLite R*Tree
    if telangana_places.is_point_in_telangana(lat, lng):
        if telangana_places.is_available():
            return await telangana_places.get_nearby_places(lat, lng, radius_m, categories)
        else:
            return ModuleResult[PlacesData](
                module="places",
                status="unavailable",
                provenance_kind="map_listing",
                data=PlacesData(
                    places=[],
                    counts_by_category={},
                    radius_m=radius_m,
                    cap_reached=False,
                    total_found=0,
                    displayed_count=0
                ),
                sources=[],
                coverage=Coverage(granularity="unknown", radius_m=radius_m, result_count=0),
                message="Telangana local places database is unavailable or not found.",
                limitations=["Dataset file missing or uninitialized. Run scripts/build_telangana_places_db.py to generate."]
            )

    # 2. Storable / open provider fallback for out-of-state coordinates
    return await overpass_places.get_nearby_places(lat, lng, radius_m, categories)

@router.get("/environment", response_model=ModuleResult[AirQualityData])
async def get_environment(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0)
):
    # If OpenAQ is configured, check station data
    if settings.OPENAQ_API_KEY:
        openaq_res = await openaq_aq.get_air_quality(lat, lng)
        if openaq_res.status == "available" and openaq_res.data:
            # Augment physical ground station air quality with Open-Meteo weather forecast
            om_res = await open_meteo_aq.get_air_quality(lat, lng)
            if om_res.data and om_res.data.weather:
                openaq_res.data.weather = om_res.data.weather
                openaq_res.data.temperature_c = om_res.data.temperature_c
                openaq_res.data.apparent_temperature_c = om_res.data.apparent_temperature_c
                openaq_res.data.humidity_pct = om_res.data.humidity_pct
                openaq_res.data.wind_speed_kmh = om_res.data.wind_speed_kmh
                openaq_res.data.precipitation_probability_pct = om_res.data.precipitation_probability_pct
                openaq_res.data.uv_index = om_res.data.uv_index
                openaq_res.data.weather_desc = om_res.data.weather_desc
            if om_res.sources:
                openaq_res.sources.extend(om_res.sources)
            return openaq_res

    # Modeled estimate from Open-Meteo (includes Copernicus CAMS air quality + Open-Meteo weather)
    return await open_meteo_aq.get_air_quality(lat, lng)

@router.get("/water", response_model=ModuleResult[WaterQualityData])
async def get_water(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    locality: str | None = Query(None)
):
    return await water_provider.get_water_quality(lat, lng, locality=locality)

@router.get("/crime", response_model=ModuleResult[SafetyAndCrimeData])
async def get_crime(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    radius_m: int = Query(3000, ge=300, le=5000)
):
    return await safety_provider.get_safety_and_crime_data(lat, lng, radius_m=radius_m)

@router.get("/safety", response_model=ModuleResult[SafetyAndCrimeData])
async def get_safety(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    radius_m: int = Query(3000, ge=300, le=5000)
):
    return await safety_provider.get_safety_and_crime_data(lat, lng, radius_m=radius_m)

@router.post("/commute", response_model=ModuleResult[CommuteData])
async def get_commute(req: CommuteRequest):
    if not req.destination_coords:
        raise HTTPException(status_code=400, detail="Destination coordinates are required for commute check.")
    
    dest_name = req.destination_query or f"{req.destination_coords.lat:.4f}, {req.destination_coords.lng:.4f}"
    res = await routes_provider.get_commute(
        origin=req.origin,
        destination_coords=req.destination_coords,
        destination_name=dest_name,
        departure_time=req.departure_time
    )

    if res.data and telangana_places.is_point_in_telangana(req.origin.lat, req.origin.lng):
        transit_places = await telangana_places.get_nearby_places(
            lat=req.origin.lat,
            lng=req.origin.lng,
            radius_m=1500,
            categories=["transport"]
        )
        if transit_places.data:
            res.data.nearby_transit_nodes_count = len(transit_places.data.places)

    return res
