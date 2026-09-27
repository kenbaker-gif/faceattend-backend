"""
Static HTML pages and public redirects served by FastAPI.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(tags=["pages"])

_STATIC = Path(__file__).resolve().parents[2] / "static"


@router.get("/")
def home():
    return FileResponse(_STATIC / "html" / "index.html")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/set-password")
def set_password_page():
    return FileResponse(_STATIC / "html" / "set-password.html")


@router.get("/reset-password")
def reset_password_page():
    return FileResponse(_STATIC / "html" / "reset-password.html")


@router.get("/dashboard")
def dashboard_page():
    return FileResponse(_STATIC / "html" / "dashboard.html")


@router.get("/privacy")
def privacy_page():
    return FileResponse(_STATIC / "html" / "privacy.html")


@router.get("/terms")
def terms_page():
    return FileResponse(_STATIC / "html" / "terms.html")


@router.get("/billing")
def billing_page():
    return FileResponse(_STATIC / "html" / "billing.html")


@router.get("/analytics")
def analytics_page():
    return FileResponse(_STATIC / "html" / "analytics.html")

@router.get("/download/faceattend.apk")
async def download_apk():
    return RedirectResponse(
        url="https://github.com/kenbaker-gif/Smart_attendance_app/releases/latest/download/app-release.apk",
    )