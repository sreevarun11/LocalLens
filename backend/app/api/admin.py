from fastapi import APIRouter, Depends
from backend.app.auth.dependencies import get_current_admin_user
from backend.app.db.repository import Repository
from backend.app.db.local_db import get_database_mode
from backend.app.config import settings
import os

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/analytics")
def get_analytics(admin_user: dict = Depends(get_current_admin_user)):
    """
    Returns platform-wide administrative analytics.
    Enforces admin-only access.
    """
    analytics = Repository.get_admin_analytics()
    return analytics

@router.get("/diagnostics")
def get_diagnostics(admin_user: dict = Depends(get_current_admin_user)):
    """
    Returns internal diagnostics and integration status.
    Keys and secrets are strictly masked and never returned.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "mode": get_database_mode(),
            "sqlite_exists": os.path.exists("backend/data/locallens_dev.db"),
            "telangana_places_db_exists": os.path.exists(settings.TELANGANA_PLACES_DB_PATH)
        },
        "flags": {
            "FEATURE_PAYMENTS": settings.FEATURE_PAYMENTS,
            "FEATURE_AI": settings.FEATURE_AI,
            "FEATURE_3D": settings.FEATURE_3D
        },
        "integrations": {
            "razorpay_configured": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
            "gemini_configured": bool(settings.GEMINI_API_KEY),
            "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
            "osrm_configured": bool(settings.OSRM_BASE_URL),
            "supabase_configured": bool(settings.SUPABASE_URL)
        }
    }
