import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    integrations=[StarletteIntegration(), FastApiIntegration()],
    traces_sample_rate=0.2,
    environment="production",
    send_default_pii=False,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from fastapi.staticfiles import StaticFiles

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "connect-src 'self' https://faceattend.app https://*.faceattend.app https://*.supabase.co https://supabase.io; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-ancestors 'none';"
        )
        return response

from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.scheduler import create_scheduler
from app.routes.auth_extra import router as auth_extra_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.notify_router import router as notify_router
from app.routes.admin_attendance import router as admin_attendance_router
from app.routes.admin_students import router as admin_students_router
from app.routes.admin_coordinators import router as admin_coordinators_router
from app.routes.admin_institutions import router as admin_institutions_router
from app.routes.pages import router as pages_router
from app.utils.mvp_sync import MVP_URL

scheduler = create_scheduler()

@asynccontextmanager
async def lifespan(app):
    scheduler.start()
 
    yield  # app runs here
 
    # ---- shutdown ----
    scheduler.shutdown()

# ── Shared dependencies (clients, limiter, auth) ───────────────────────────
from .dep import limiter

# ── Enterprise API v1 router ───────────────────────────────────────────────
from app.routes.v1_api import router as v1_router
from app.routes.pesapal_router import router as pesapal_router

load_dotenv()

app = FastAPI(
    title="Smart Attendance — Upload Service",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom validation error handler to log detailed validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"[VALIDATION_ERROR] Endpoint: {request.url.path} | Method: {request.method}")
    logger.error(f"[VALIDATION_ERROR] Errors: {exc.errors()}")
    logger.error(f"[VALIDATION_ERROR] Body: {exc.body if hasattr(exc, 'body') else 'N/A'}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body) if hasattr(exc, 'body') else None},
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "https://faceattend.app,https://www.faceattend.app,https://api.faceattend.app,https://mvp.faceattend.app",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"^https://([\w-]+\.)*faceattend\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.add_middleware(SecurityHeadersMiddleware)

if not os.getenv("SUPABASE_ANON_KEY"):
    raise RuntimeError("SUPABASE_ANON_KEY environment variable is required")

if not MVP_URL:
    print("⚠️  WARNING: MVP_URL is not set. Auto-sync after photo upload will be disabled.")
else:
    print(f"✅ MVP_URL = {MVP_URL}")

# ── Mount Enterprise API v1 ────────────────────────────────────────────────
app.include_router(v1_router)
app.include_router(pesapal_router)
app.include_router(auth_extra_router)   # /auth/forgot-password, /auth/log-login, /webhooks/supabase-auth
app.include_router(audit_logs_router)   # /audit-logs, /audit-logs/actions
app.include_router(notify_router)
app.include_router(admin_attendance_router)
app.include_router(admin_students_router)
app.include_router(admin_coordinators_router)
app.include_router(admin_institutions_router)
app.include_router(pages_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
