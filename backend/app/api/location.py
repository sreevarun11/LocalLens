from fastapi import APIRouter, HTTPException, Query
from backend.app.providers.geocoding import GoogleGeocodingProvider, PhotonGeocodingProvider
from backend.app.schemas.location import AutocompletePrediction, LocationDetails
from backend.app.config import settings

router = APIRouter(prefix="/location", tags=["Location"])

google_geocoder = GoogleGeocodingProvider()
photon_geocoder = PhotonGeocodingProvider()

@router.get("/autocomplete", response_model=list[AutocompletePrediction])
async def autocomplete(
    query: str = Query(..., min_length=2, description="Search query string"),
    session_token: str | None = Query(None, description="Optional Google session token")
):
    if settings.GOOGLE_MAPS_SERVER_KEY:
        preds = await google_geocoder.autocomplete(query, session_token)
        if preds:
            return preds
            
    # Open fallback provider
    preds = await photon_geocoder.autocomplete(query, session_token)
    return preds

@router.get("/details", response_model=LocationDetails)
async def get_details(
    place_id: str = Query(..., description="Place ID or coordinate identifier"),
    session_token: str | None = Query(None, description="Optional Google session token")
):
    if settings.GOOGLE_MAPS_SERVER_KEY and not place_id.startswith("photon_") and not place_id.startswith("coords_"):
        details = await google_geocoder.get_details(place_id, session_token)
        if details:
            return details

    details = await photon_geocoder.get_details(place_id, session_token)
    if details:
        return details

    raise HTTPException(status_code=404, detail="Location details not found for the requested place ID.")

@router.get("/reverse", response_model=LocationDetails)
async def reverse_geocode(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0)
):
    if settings.GOOGLE_MAPS_SERVER_KEY:
        details = await google_geocoder.reverse_geocode(lat, lng)
        if details:
            return details

    details = await photon_geocoder.reverse_geocode(lat, lng)
    if details:
        return details

    raise HTTPException(status_code=404, detail="Unable to resolve coordinates to an address.")
