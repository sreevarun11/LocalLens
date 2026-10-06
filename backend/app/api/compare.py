import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.schemas.base import ModuleResult
from backend.app.schemas.location import PlacesData
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData
from backend.app.providers.places import OverpassPlacesProvider, GooglePlacesProvider
from backend.app.providers.environment import OpenMeteoAirQualityProvider, DefaultWaterQualityProvider, DefaultCrimeProvider
from backend.app.evidence.comparison import ComparisonEngine, LocalityComparisonSummary
from backend.app.evidence.personalization import PriorityKey
from backend.app.config import settings

router = APIRouter(prefix="/compare", tags=["Locality Comparison"])

overpass_provider = OverpassPlacesProvider()
google_places_provider = GooglePlacesProvider()
open_meteo_provider = OpenMeteoAirQualityProvider()
water_provider = DefaultWaterQualityProvider()
crime_provider = DefaultCrimeProvider()

class CompareRequest(BaseModel):
    loc_a_name: str
    loc_a_lat: float
    loc_a_lng: float
    loc_b_name: str
    loc_b_lat: float
    loc_b_lng: float
    priorities: list[PriorityKey] | None = None
    load_water_crime: bool = False

@router.post("", response_model=LocalityComparisonSummary)
async def compare_localities(req: CompareRequest):
    places_prov = google_places_provider if settings.GOOGLE_MAPS_SERVER_KEY else overpass_provider

    # Parallel fetch for both localities
    tasks = [
        places_prov.get_nearby_places(req.loc_a_lat, req.loc_a_lng, 1500),
        places_prov.get_nearby_places(req.loc_b_lat, req.loc_b_lng, 1500),
        open_meteo_provider.get_air_quality(req.loc_a_lat, req.loc_a_lng),
        open_meteo_provider.get_air_quality(req.loc_b_lat, req.loc_b_lng)
    ]

    should_load_water_crime = req.load_water_crime or settings.FEATURE_COMPARE_LOAD_ALL
    if should_load_water_crime:
        tasks.extend([
            water_provider.get_water_quality(req.loc_a_lat, req.loc_a_lng),
            water_provider.get_water_quality(req.loc_b_lat, req.loc_b_lng),
            crime_provider.get_crime_data(req.loc_a_lat, req.loc_a_lng),
            crime_provider.get_crime_data(req.loc_b_lat, req.loc_b_lng)
        ])

    results = await asyncio.gather(*tasks, return_exceptions=True)

    places_a = results[0] if not isinstance(results[0], Exception) else None
    places_b = results[1] if not isinstance(results[1], Exception) else None
    env_a = results[2] if not isinstance(results[2], Exception) else None
    env_b = results[3] if not isinstance(results[3], Exception) else None

    water_a = results[4] if should_load_water_crime and not isinstance(results[4], Exception) else None
    water_b = results[5] if should_load_water_crime and not isinstance(results[5], Exception) else None
    crime_a = results[6] if should_load_water_crime and not isinstance(results[6], Exception) else None
    crime_b = results[7] if should_load_water_crime and not isinstance(results[7], Exception) else None

    summary = ComparisonEngine.compare_localities(
        loc_a_name=req.loc_a_name,
        loc_b_name=req.loc_b_name,
        places_a=places_a,
        places_b=places_b,
        env_a=env_a,
        env_b=env_b,
        water_a=water_a,
        water_b=water_b,
        crime_a=crime_a,
        crime_b=crime_b,
        priorities=req.priorities
    )

    return summary
