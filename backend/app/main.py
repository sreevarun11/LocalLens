import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.db.local_db import init_db
from backend.app.api.health import router as health_router
from backend.app.api.location import router as location_router
from backend.app.api.modules import router as modules_router
from backend.app.api.insights import router as insights_router
from backend.app.api.compare import router as compare_router
from backend.app.api.ai import router as ai_router
from backend.app.api.auth import router as auth_router
from backend.app.api.user import router as user_router
from backend.app.api.reports import router as reports_router
from backend.app.api.payments import router as payments_router
from backend.app.api.admin import router as admin_router

# Setup structured logging without leaking PII or secrets
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("locallens")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="LocalLens API — Real neighborhood intelligence without fabrication"
)

# CORS middleware
try:
    allowed_cors_origins = settings.get_cors_origins()
except Exception:
    allowed_cors_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Production security validation
    if settings.ENVIRONMENT == "production":
        settings.get_jwt_secret()
        settings.get_cors_origins()

    init_db()
    from backend.app.db.repository import Repository
    Repository.provision_admin_user(settings.ADMIN_USERNAME, getattr(settings, "ADMIN_PASSWORD", None))
    logger.info("LocalLens database initialized and administrator provisioned.")

# Custom error format handler: { "error": { "code": "...", "message": "..." } }
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            }
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later."
            }
        }
    )

# Include Routers
app.include_router(health_router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(modules_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(compare_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(reports_router)
app.include_router(payments_router)
app.include_router(admin_router)

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs"
    }
