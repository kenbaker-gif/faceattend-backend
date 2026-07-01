"""
Centralized configuration management.
"""
import os
from typing import List

class Settings:
    # App
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8080")
    MVP_URL: str = os.getenv("MVP_URL", "")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SERVICE_KEY: str = os.getenv("SERVICE_KEY", "")
    
    # Pesapal
    PESAPAL_ENV: str = os.getenv("PESAPAL_ENV", "sandbox")
    PESAPAL_CONSUMER_KEY: str = os.getenv("PESAPAL_CONSUMER_KEY", "")
    PESAPAL_CONSUMER_SECRET: str = os.getenv("PESAPAL_CONSUMER_SECRET", "")
    
    # Email
    ZOHO_SMTP_USER: str = os.getenv("ZOHO_SMTP_USER", "")
    ZOHO_REFRESH_TOKEN: str = os.getenv("ZOHO_REFRESH_TOKEN", "")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    
    # AI
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Monitoring
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    
    # CORS
    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = os.getenv("CORS_ORIGINS", "")
        if origins:
            return [o.strip() for o in origins.split(",")]
        return ["http://localhost:3000", "http://localhost:8080"]

settings = Settings()
# Backwards-compatible lowercase aliases expected by tests
settings.supabase_url = settings.SUPABASE_URL
settings.supabase_key = settings.SUPABASE_KEY
settings.pesapal_env = settings.PESAPAL_ENV
settings.email_from = settings.ZOHO_SMTP_USER
