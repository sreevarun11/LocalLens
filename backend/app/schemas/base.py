from datetime import datetime
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class DataSourceInfo(BaseModel):
    name: str
    url: str | None = None
    license: str | None = None
    attribution: str | None = None

class Coverage(BaseModel):
    granularity: Literal[
        "exact_place",
        "nearby_place",
        "monitoring_station",
        "city",
        "district",
        "state",
        "unknown"
    ] = "unknown"
    radius_m: int | None = None
    result_count: int | None = None
    result_cap_reached: bool | None = None  # If True, count is a LOWER BOUND
    nearest_distance_m: int | None = None
    station_distance_m: int | None = None
    note: str | None = None

class ModuleResult(BaseModel, Generic[T]):
    module: str
    status: Literal["available", "limited", "unavailable", "error"]
    provenance_kind: Literal[
        "station_measurement",
        "official_dataset",
        "map_listing",
        "modeled_estimate",
        "user_provided",
        "derived"
    ]
    data: T | None = None
    sources: list[DataSourceInfo] = Field(default_factory=list)
    coverage: Coverage
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    source_updated_at: datetime | None = None
    measured_at: datetime | None = None
    limitations: list[str] = Field(default_factory=list)
    message: str | None = None
    served_from: Literal["live", "demo_snapshot"] = "live"

class EvidenceEntity(BaseModel):
    name: str
    place_id: str | None = None
    lat: float
    lng: float
    distance_m: int
    category: str

class EvidenceItem(BaseModel):
    id: str  # stable e.g. "loc1:education:nearest_distance_m"
    locality_key: str
    module: str
    metric: str
    value: float | int | str | None = None
    unit: str | None = None
    radius_m: int | None = None
    result_cap_reached: bool | None = None
    entities: list[EvidenceEntity] = Field(default_factory=list)
    provenance_kind: str
    granularity: str
    source: DataSourceInfo
    fetched_at: datetime
    measured_at: datetime | None = None
    source_updated_at: datetime | None = None
    limitations: list[str] = Field(default_factory=list)

class EvidenceGap(BaseModel):
    module: str
    reason: str
    granularity_needed: str
