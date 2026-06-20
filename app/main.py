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
import logging

from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.scheduler import create_scheduler
from app.routes.auth import router as auth_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.notifications import router as notifications_router
from app.routes.admin.attendance import router as admin_attendance_router
from app.routes.admin.students import router as admin_students_router
from app.routes.admin.coordinators import router as admin_coordinators_router
from app.routes.admin.institutions import router as admin_institutions_router
from app.routes.admin.sessions import router as admin_sessions_router
from app.routes.admin.billing import router as admin_billing_router
from app.routes.admin.auto_renewal import router as admin_auto_renewal_router
from app.routes.admin.analytics import router as admin_analytics_router
from app.routes.pages import router as pages_router
from app.routes.api.v1 import router as v1_router
from app.routes.webhooks.pesapal import router as pesapal_router
from app.config import settings
from app.dep import limiter
from app.utils.mvp_sync import MVP_URL
from app.middleware.security import SecurityHeadersMiddleware

scheduler = create_scheduler()

@asynccontextmanager
async def lifespan(app):
    scheduler.start()
    yield
    scheduler.shutdown()

load_dotenv()

app = FastAPI(
    title="FaceAttend API",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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

# ── Mount routers ──────────────────────────────────────────────────────────
app.include_router(v1_router)
app.include_router(pesapal_router)
app.include_router(auth_router)
app.include_router(audit_logs_router)
app.include_router(notifications_router)
app.include_router(admin_attendance_router)
app.include_router(admin_students_router)
app.include_router(admin_coordinators_router)
app.include_router(admin_institutions_router)
app.include_router(admin_sessions_router)
app.include_router(admin_billing_router)
app.include_router(admin_auto_renewal_router)
app.include_router(admin_analytics_router)
app.include_router(pages_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
