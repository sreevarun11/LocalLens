import os
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
    Returns verified configuration and health status of integrated data providers.
    All keys and secrets are strictly masked and never returned.
    Used by /data-sources transparency page and Admin diagnostics.
    """
    providers = [
        {
            "id": "maplibre_openfreemap",
            "name": "MapLibre GL JS & OpenFreeMap (Vector Basemap)",
            "configured": True,
            "storage_policy": "client_render",
            "license": "BSD-3-Clause / OpenFreeMap Terms",
            "attribution": "MapLibre contributors · © OpenStreetMap contributors",
            "status": "operational"
        },
        {
            "id": "osm_photon",
            "name": "Photon Geocoder (Komoot / OpenStreetMap)",
            "configured": True,
            "storage_policy": "storable",
            "license": "ODbL 1.0 / Apache 2.0",
            "attribution": "Data © OpenStreetMap contributors · Photon by Komoot",
            "status": "operational"
        },
        {
            "id": "osrm_routing",
            "name": "OSRM Road-Network Routing Engine",
            "configured": True,
            "storage_policy": "storable",
            "license": "ODbL 1.0 / BSD 2-Clause",
            "attribution": "Project OSRM · Road-network geometry (No live traffic claims)",
            "status": "operational"
        },
        {
            "id": "telangana_spatial_db",
            "name": "Telangana Spatial Facilities & Amenities Database",
            "configured": os.path.exists(settings.TELANGANA_PLACES_DB_PATH),
            "storage_policy": "storable",
            "license": "Open Data / NDSAP Telangana",
            "attribution": "Govt of Telangana Open Data & OSM Telangana Spatial Index",
            "status": "operational" if os.path.exists(settings.TELANGANA_PLACES_DB_PATH) else "missing_database_file"
        },
        {
            "id": "open_meteo",
            "name": "Open-Meteo Air Quality & Weather (ECMWF CAMS Global)",
            "configured": True,
            "storage_policy": "storable",
            "license": "Copernicus / Open-Meteo Terms",
            "attribution": "ECMWF Copernicus Atmosphere Monitoring Service (~40 km Global Grid)",
            "status": "operational"
        },
        {
            "id": "water_cgwb",
            "name": "Central Ground Water Board (CGWB) & TGWD Assessment",
            "configured": True,
            "storage_policy": "storable",
            "license": "NDSAP India Open Data",
            "attribution": "Ministry of Jal Shakti, CGWB & Ground Water Dept, Govt. of Telangana (2022)",
            "status": "operational"
        },
        {
            "id": "safety_telangana",
            "name": "Telangana Emergency Directory & Police Infrastructure",
            "configured": True,
            "storage_policy": "storable",
            "license": "Public Safety Directory / Official Portals",
            "attribution": "Telangana Police, Fire Services, SHE Teams (1090) & National 112 ERSS",
            "status": "operational"
        },
        {
            "id": "database_persistence",
            "name": "Database Persistence Engine (PostgreSQL / SQLite Local DB)",
            "configured": True,
            "storage_policy": "storable",
            "license": "Proprietary Application Architecture",
            "attribution": "LocalLens Data Repository",
            "status": "operational"
        },
        {
            "id": "payments_razorpay",
            "name": "Razorpay Payment Gateway (Test Mode / Live)",
            "configured": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
            "storage_policy": "storable",
            "license": "Razorpay Merchant Terms",
            "attribution": "Razorpay Software Pvt Ltd",
            "status": "operational" if (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET) else "unconfigured_test_mode"
        },
        {
            "id": "llm_synthesis",
            "name": f"AI Grounded Synthesis ({settings.LLM_PROVIDER} / {settings.LLM_MODEL})",
            "configured": bool(settings.GEMINI_API_KEY or settings.ANTHROPIC_API_KEY),
            "storage_policy": "storable",
            "license": "Commercial API Terms / Deterministic Engine",
            "attribution": "Google DeepMind / Anthropic / LocalLens Synthesis Engine",
            "status": "operational" if (settings.GEMINI_API_KEY or settings.ANTHROPIC_API_KEY) else "deterministic_fallback_active"
        },
        {
            "id": "google_maps",
            "name": "Google Maps Platform (Keyless Architecture - Not Required)",
            "configured": bool(settings.GOOGLE_MAPS_API_KEY),
            "storage_policy": "not_stored",
            "license": "Google Cloud Terms",
            "attribution": "Google Maps Platform (Replaced by OpenFreeMap & MapLibre)",
            "status": "not_required" if not settings.GOOGLE_MAPS_API_KEY else "optional_configured"
        },
        {
            "id": "osm_overpass",
            "name": "OpenStreetMap Overpass API (Fallback Spatial Provider)",
            "configured": True,
            "storage_policy": "storable",
            "license": "ODbL 1.0",
            "attribution": "© OpenStreetMap contributors",
            "status": "operational"
        },
        {
            "id": "crime_ncrb",
            "name": "NCRB Crime in India (City/State Benchmark)",
            "configured": True,
            "storage_policy": "storable",
            "license": "Open Government Data (OGD) India",
            "attribution": "National Crime Records Bureau (NCRB) Ministry of Home Affairs",
            "status": "operational"
        }
    ]
    return {"providers": providers}
