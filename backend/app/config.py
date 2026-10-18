from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    APP_NAME: str = "LocalLens"
    VERSION: str = "4.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    
    # Feature flags
    FEATURE_PAYMENTS: bool = True
    FEATURE_3D: bool = False
    FEATURE_AI: bool = True
    DEMO_SNAPSHOT_MODE: bool = False
    FEATURE_COMPARE_LOAD_ALL: bool = False
    
    # Database & Persistence
    DATABASE_URL: str | None = None

    # API Keys & Secrets
    GOOGLE_MAPS_SERVER_KEY: str | None = None
    GOOGLE_MAPS_API_KEY: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_SECRET_KEY: str | None = None
    SUPABASE_PUBLISHABLE_KEY: str | None = None
    SUPABASE_JWT_SECRET: str | None = None
    ADMIN_SECRET_KEY: str | None = None
    ADMIN_USERNAME: str = "sreevarun"
    ADMIN_PASSWORD: str | None = None
    
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None
    
    OPENAQ_API_KEY: str | None = None
    OVERPASS_URL: str = "https://z.overpass-api.de/api/interpreter"
    TELANGANA_PLACES_DB_PATH: str = "backend/data/telangana_places.db"
    OSRM_BASE_URL: str = "http://router.project-osrm.org"
    ROUTING_PROVIDER: Literal["osrm", "google"] = "osrm"
    
    # LLM Settings
    LLM_PROVIDER: Literal["gemini", "anthropic"] = "gemini"
    LLM_MODEL: str = "gemini-1.5-flash"
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    AI_DAILY_LIMIT_PER_USER: int = 10
    
    # Application & Business Constants
    REPORT_PRICE_PAISE: int = 2900
    CONTACT_EMAIL: str = "support@locallens.app"
    APP_BASE_URL: str = "http://localhost:5173"
    PUBLIC_BASE_URL: str | None = None
    CORS_ORIGINS: str = ""
    
    def get_public_base_url(self) -> str:
        """
        Returns the public base URL for verification links and QR codes.
        Fails loudly if resolving to localhost in a production environment.
        """
        raw_url = (self.PUBLIC_BASE_URL or self.APP_BASE_URL or "http://localhost:5173").rstrip("/")
        if self.ENVIRONMENT == "production":
            lower_url = raw_url.lower()
            if not self.PUBLIC_BASE_URL or "localhost" in lower_url or "127.0.0.1" in lower_url:
                raise ValueError("PUBLIC_BASE_URL must be configured with a non-localhost domain in production.")
        return raw_url

    def get_jwt_secret(self) -> str:
        """
        Returns the JWT secret for token cryptographic signing.
        Fails loudly in production if missing, empty, or insecure.
        """
        secret = self.SUPABASE_JWT_SECRET
        if self.ENVIRONMENT == "production":
            if not secret or len(secret) < 32 or secret == "locallens_super_secure_secret_key_4.0":
                raise RuntimeError(
                    "SUPABASE_JWT_SECRET must be configured with a secure key (at least 32 characters) in production."
                )
            return secret
        return secret or "locallens_dev_jwt_secret_insecure_fallback"

    def get_cors_origins(self) -> list[str]:
        """
        Returns list of allowed CORS origins.
        In production, requires explicit domains (e.g. from CORS_ORIGINS or PUBLIC_BASE_URL).
        Disallows wildcard '*' when credentials are enabled.
        """
        origins: list[str] = []
        if self.CORS_ORIGINS:
            origins.extend([o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()])
        if self.PUBLIC_BASE_URL:
            pub = self.PUBLIC_BASE_URL.strip().rstrip("/")
            if pub and pub not in origins and "localhost" not in pub.lower() and "127.0.0.1" not in pub:
                origins.append(pub)
        if self.ENVIRONMENT != "production":
            # Local development defaults
            dev_defaults = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
            for d in dev_defaults:
                if d not in origins:
                    origins.append(d)
        elif not origins:
            raise ValueError("CORS_ORIGINS or PUBLIC_BASE_URL must be configured with a production domain in production.")
        return origins

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
