from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "flags": {
            "FEATURE_PAYMENTS": settings.FEATURE_PAYMENTS,
            "FEATURE_3D": settings.FEATURE_3D,
            "FEATURE_AI": settings.FEATURE_AI,
            "DEMO_SNAPSHOT_MODE": settings.DEMO_SNAPSHOT_MODE,
            "FEATURE_COMPARE_LOAD_ALL": settings.FEATURE_COMPARE_LOAD_ALL
        }
    }

@router.get("/health/providers")
async def provider_health():
    """
    Returns real configuration and health status of integrated data providers.
    Used by the /data-sources transparency page.
    """
    providers = [
        {
            "id": "google_maps",
            "name": "Google Maps Platform (Places, Geocoding, Routes, Maps JS)",
            "configured": bool(settings.GOOGLE_MAPS_SERVER_KEY),
            "storage_policy": "live_only",
            "license": "Google Maps Platform Terms",
            "attribution": "Powered by Google",
            "status": "operational" if settings.GOOGLE_MAPS_SERVER_KEY else "unconfigured_server_key"
        },
        {
            "id": "osm_overpass",
            "name": "OpenStreetMap via Overpass API",
            "configured": True,
            "storage_policy": "storable",
            "license": "ODbL 1.0",
            "attribution": "Data © OpenStreetMap contributors",
            "status": "operational"
        },
        {
            "id": "open_meteo",
            "name": "Open-Meteo Air Quality (Copernicus CAMS)",
            "configured": True,
            "storage_policy": "storable",
            "license": "Open-Meteo / Copernicus Terms",
            "attribution": "European Atmosphere Monitoring Service reanalysis",
            "status": "operational"
        },
        {
            "id": "openaq",
            "name": "OpenAQ Ground Station Measurements",
            "configured": bool(settings.OPENAQ_API_KEY),
            "storage_policy": "storable",
            "license": "CC BY 4.0",
            "attribution": "OpenAQ Contributors",
            "status": "operational" if settings.OPENAQ_API_KEY else "unconfigured"
        },
        {
            "id": "water_cgwb",
            "name": "Central Ground Water Board (CGWB)",
            "configured": False,
            "storage_policy": "storable",
            "license": "NDSAP India",
            "attribution": "Government of India",
            "status": "no_locality_machine_api"
        },
        {
            "id": "crime_ncrb",
            "name": "National Crime Records Bureau (NCRB)",
            "configured": False,
            "storage_policy": "storable",
            "license": "OGD India",
            "attribution": "Ministry of Home Affairs",
            "status": "district_level_only_no_locality_api"
        },
        {
            "id": "llm_synthesis",
            "name": f"AI Synthesis ({settings.LLM_PROVIDER} / {settings.LLM_MODEL})",
            "configured": bool(settings.GEMINI_API_KEY or settings.ANTHROPIC_API_KEY),
            "storage_policy": "storable",
            "license": "Commercial API Terms",
            "attribution": "Google DeepMind / Anthropic",
            "status": "operational" if (settings.GEMINI_API_KEY or settings.ANTHROPIC_API_KEY) else "unconfigured_fallback_active"
        },
        {
            "id": "payments_razorpay",
            "name": "Razorpay Payment Gateway",
            "configured": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
            "storage_policy": "storable",
            "license": "Razorpay Terms",
            "attribution": "Razorpay Software Pvt Ltd",
            "status": "operational" if (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET) else "unconfigured"
        }
    ]
    return {"providers": providers}
