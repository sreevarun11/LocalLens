from pydantic import BaseModel, Field
from typing import Literal
from backend.app.schemas.location import Coordinates

class WeatherData(BaseModel):
    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    humidity_pct: int | None = None
    wind_speed_kmh: float | None = None
    wind_direction_deg: int | None = None
    precipitation_mm: float | None = None
    precipitation_probability_pct: int | None = None
    uv_index: float | None = None
    weather_desc: str | None = None
    forecast_time: str | None = None

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
    weather: WeatherData | None = None
    # Weather shortcuts
    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    humidity_pct: int | None = None
    wind_speed_kmh: float | None = None
    precipitation_probability_pct: int | None = None
    uv_index: float | None = None
    weather_desc: str | None = None

class WaterQualityData(BaseModel):
    sample_count: int = 0
    tds_mg_l: float | None = None
    ph: float | None = None
    hardness_mg_l: float | None = None
    sample_date: str | None = None
    data_level: Literal["property", "locality", "mandal", "city", "district", "state", "unknown"] = "unknown"
    # Official Ground Water Resources Assessment fields
    district_name: str | None = None
    district_code: str | None = None
    mandal_name: str | None = None
    assessment_category: str | None = None  # Safe, Semi-Critical, Critical, Over-Exploited
    stage_of_extraction_pct: float | None = None  # None when data_level == 'mandal' and mandal % is unverified
    mandal_stage_of_extraction_pct: float | None = None  # Mandal extraction % if published
    district_stage_of_extraction_pct: float | None = None  # District aggregate extraction %
    annual_extractable_ham: float | None = None
    annual_extraction_ham: float | None = None
    water_table_pre_monsoon_mbgl: float | None = None
    water_table_post_monsoon_mbgl: float | None = None
    seasonal_water_table_rise_m: float | None = None
    reporting_year: str | None = None
    assessment_methodology: str | None = None
    mandals_summary: str | None = None
    tds_range_mg_l: str | None = None
    ph_range: str | None = None
    is_historical_baseline: bool = True
    dataset_publication: str | None = None
    geographic_resolution: str | None = None
    disclaimer: str | None = None

class CrimeData(BaseModel):
    incident_count: int | None = None
    rate_per_100k: float | None = None
    data_granularity: Literal["locality", "police_station", "district", "commissionerate", "state"] = "district"
    reporting_year: int | None = None
    source_agency: str | None = None

class SafetyFacility(BaseModel):
    id: str
    name: str
    facility_type: Literal["police", "fire_station"]
    lat: float
    lng: float
    distance_m: int
    distance_km: float
    address: str | None = None
    source_name: str = "OpenStreetMap (Telangana Statewide Extract)"
    source_attribution: str | None = "https://www.openstreetmap.org/copyright"

class EmergencyContact(BaseModel):
    service: str
    number: str
    description: str
    jurisdiction: str
    verified_authority: str
    source_url: str
    last_verified_at: str | None = "2026-10-16"
    limitations: list[str] = Field(default_factory=list)

class JurisdictionInfo(BaseModel):
    jurisdiction_name: str | None = None
    jurisdiction_type: Literal["commissionerate", "district_police", "unavailable"] = "unavailable"
    supporting_authority: str | None = None
    source_url: str | None = None
    geographic_resolution: str | None = None
    limitations: list[str] = Field(default_factory=list)

class SafetyAndCrimeData(CrimeData):
    nearby_facilities: list[SafetyFacility] = Field(default_factory=list)
    emergency_contacts: list[EmergencyContact] = Field(default_factory=list)
    jurisdiction: JurisdictionInfo = Field(default_factory=JurisdictionInfo)
    crime_statistics_status: Literal["available", "unavailable"] = "unavailable"
    crime_disclosure_note: str = (
        "Verified locality-level crime statistics are not available in the connected public dataset. "
        "District or commissionerate statistics cannot reliably determine crime levels for an individual neighborhood."
    )
    absence_caveat: str = (
        "The absence of published locality-level crime statistics does not imply that an area is safe."
    )

class CommuteRequest(BaseModel):
    origin: Coordinates
    destination_place_id: str | None = None
    destination_query: str | None = None
    destination_coords: Coordinates | None = None
    departure_time: str | None = None

class CommuteModeResult(BaseModel):
    mode: Literal["driving", "transit", "walking", "two_wheeler"]
    duration_min: int | None = None
    duration_s: float | None = None
    distance_km: float | None = None
    distance_m: float | None = None
    status: Literal["available", "unavailable", "error"]
    route_summary: str | None = None
    route_geometry: list[list[float]] | None = None
    provider: str = "OSRM Road-Network Engine"
    fare: str | None = None
    data_kind: Literal["road_network_estimate", "live_traffic", "timetable_schedule", "unavailable"] = "road_network_estimate"
    limitations: list[str] = Field(default_factory=list)

class CommuteData(BaseModel):
    origin_coords: Coordinates | None = None
    destination_name: str
    destination_coords: Coordinates | None = None
    modes: dict[str, CommuteModeResult] = Field(default_factory=dict)
    nearby_transit_nodes_count: int | None = None
    traffic_claim: str = "Nominal road-network routing estimate under standard road speeds. Live traffic conditions, signal delays, and temporary congestion are not factored."
