from pydantic import BaseModel, Field
from typing import Literal

class AutocompletePrediction(BaseModel):
    place_id: str
    description: str
    main_text: str
    secondary_text: str | None = None
    provider: str = "google"

class Coordinates(BaseModel):
    lat: float
    lng: float

class CanonicalLocation(BaseModel):
    place_id: str
    formatted_address: str
    name: str
    latitude: float = 0.0
    longitude: float = 0.0
    lat: float = 0.0
    lng: float = 0.0
    district: str | None = None
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    provider: str

    def __init__(self, **data):
        if "lat" in data and ("latitude" not in data or data["latitude"] == 0.0):
            data["latitude"] = data["lat"]
        elif "latitude" in data and ("lat" not in data or data["lat"] == 0.0):
            data["lat"] = data["latitude"]
        if "lng" in data and ("longitude" not in data or data["longitude"] == 0.0):
            data["longitude"] = data["lng"]
        elif "longitude" in data and ("lng" not in data or data["lng"] == 0.0):
            data["lng"] = data["longitude"]
        super().__init__(**data)

LocationDetails = CanonicalLocation

class PlaceItem(BaseModel):
    id: str
    name: str
    category: Literal[
        "healthcare",
        "education",
        "safety_infrastructure",
        "daily_life",
        "transport",
        "lifestyle"
    ]
    subcategory: str | None = None
    lat: float
    lng: float
    distance_m: int  # Straight-line distance from locality center
    address: str | None = None
    rating: float | None = None
    user_ratings_total: int | None = None
    source_name: str
    source_attribution: str | None = None

class PlacesData(BaseModel):
    places: list[PlaceItem] = Field(default_factory=list)
    counts_by_category: dict[str, int] = Field(default_factory=dict)
    radius_m: int
    cap_reached: bool = False
