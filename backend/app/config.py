from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    APP_NAME: str = "LocalLens"
    VERSION: str = "4.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    
    # Feature flags
    FEATURE_PAYMENTS: bool = False
    FEATURE_3D: bool = False
    FEATURE_AI: bool = True
    DEMO_SNAPSHOT_MODE: bool = False
    FEATURE_COMPARE_LOAD_ALL: bool = False
    
    # API Keys & Secrets
    GOOGLE_MAPS_SERVER_KEY: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_SECRET: str | None = None
    
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None
    
    OPENAQ_API_KEY: str | None = None
    OVERPASS_URL: str = "https://z.overpass-api.de/api/interpreter"
    
    # LLM Settings
    LLM_PROVIDER: Literal["gemini", "anthropic"] = "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    AI_DAILY_LIMIT_PER_USER: int = 10
    
    # Application & Business Constants
    REPORT_PRICE_PAISE: int = 2900
    CONTACT_EMAIL: str = "support@locallens.app"
    APP_BASE_URL: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
