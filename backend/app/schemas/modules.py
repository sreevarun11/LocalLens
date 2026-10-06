from pydantic import BaseModel, Field
from typing import Literal
from backend.app.schemas.location import Coordinates

class AirQualityData(BaseModel):
    aqi: int | None = None
    aqi_scale: str = "US AQI"
    pm25: float | None = None
    pm10: float | None = None
    co: float | None = None
    no2: float | None = None
    o3: float | None = None
    so2: float | None = None
    station_name: str | None = None
    station_distance_m: int | None = None
    station_coordinates: Coordinates | None = None
    model_grid_resolution_km: float | None = None
    dominant_pollutant: str | None = None
    advisory: str | None = None

class WaterQualityData(BaseModel):
    sample_count: int = 0
    tds_mg_l: float | None = None
    ph: float | None = None
    hardness_mg_l: float | None = None
    sample_date: str | None = None
    data_level: Literal["property", "locality", "city", "district", "state", "unknown"] = "unknown"

class CrimeData(BaseModel):
    incident_count: int | None = None
    rate_per_100k: float | None = None
    data_granularity: Literal["locality", "police_station", "district", "commissionerate", "state"] = "district"
    reporting_year: int | None = None
    source_agency: str | None = None

class CommuteRequest(BaseModel):
    origin: Coordinates
    destination_place_id: str | None = None
    destination_query: str | None = None
    destination_coords: Coordinates | None = None
    departure_time: str | None = None

class CommuteModeResult(BaseModel):
    mode: Literal["driving", "transit", "walking", "two_wheeler"]
    duration_min: int | None = None
    distance_km: float | None = None
    status: Literal["available", "unavailable", "error"]
    route_summary: str | None = None
    provider: str = "Google Routes"
    fare: str | None = None

class CommuteData(BaseModel):
    destination_name: str
    destination_coords: Coordinates | None = None
    modes: dict[str, CommuteModeResult] = Field(default_factory=dict)
