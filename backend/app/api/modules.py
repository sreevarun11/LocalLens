from fastapi import APIRouter, Query, HTTPException
from backend.app.schemas.base import ModuleResult
from backend.app.schemas.location import PlacesData, Coordinates
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, CommuteData, CommuteRequest
from backend.app.providers.places import OverpassPlacesProvider, GooglePlacesProvider
from backend.app.providers.environment import (
    OpenMeteoAirQualityProvider,
    OpenAQAirQualityProvider,
    DefaultWaterQualityProvider,
    DefaultCrimeProvider
)
from backend.app.providers.routing import GoogleRoutesProvider
from backend.app.config import settings

router = APIRouter(prefix="/modules", tags=["Modules"])

overpass_places = OverpassPlacesProvider()
google_places = GooglePlacesProvider()
open_meteo_aq = OpenMeteoAirQualityProvider()
openaq_aq = OpenAQAirQualityProvider()
water_provider = DefaultWaterQualityProvider()
crime_provider = DefaultCrimeProvider()
routes_provider = GoogleRoutesProvider()

@router.get("/places", response_model=ModuleResult[PlacesData])
async def get_places(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    radius_m: int = Query(1500, ge=300, le=5000),
    categories: list[str] | None = Query(None)
):
    # If Google Maps server key is set, try live Google Places; otherwise use Overpass OSM
    if settings.GOOGLE_MAPS_SERVER_KEY:
        res = await google_places.get_nearby_places(lat, lng, radius_m, categories)
        if res.status != "error":
            return res

    # Storable / open provider fallback
    return await overpass_places.get_nearby_places(lat, lng, radius_m, categories)

@router.get("/environment", response_model=ModuleResult[AirQualityData])
async def get_environment(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0)
):
    # If OpenAQ is configured, check station data
    if settings.OPENAQ_API_KEY:
        openaq_res = await openaq_aq.get_air_quality(lat, lng)
        if openaq_res.status == "available":
            return openaq_res

    # Modeled estimate from Open-Meteo
    return await open_meteo_aq.get_air_quality(lat, lng)

@router.get("/water", response_model=ModuleResult[WaterQualityData])
async def get_water(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0)
):
    return await water_provider.get_water_quality(lat, lng)

@router.get("/crime", response_model=ModuleResult[CrimeData])
async def get_crime(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0)
):
    return await crime_provider.get_crime_data(lat, lng)

@router.post("/commute", response_model=ModuleResult[CommuteData])
async def get_commute(req: CommuteRequest):
    if not req.destination_coords:
        raise HTTPException(status_code=400, detail="Destination coordinates are required for commute check.")
    
    dest_name = req.destination_query or f"{req.destination_coords.lat:.4f}, {req.destination_coords.lng:.4f}"
    return await routes_provider.get_commute(
        origin=req.origin,
        destination_coords=req.destination_coords,
        destination_name=dest_name,
        departure_time=req.departure_time
    )
