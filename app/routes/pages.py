"""
Static HTML pages and public redirects served by FastAPI.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(tags=["pages"])

_STATIC = Path(__file__).resolve().parents[2] / "static"


@router.get("/favicon.ico")
def favicon():
    return FileResponse(_STATIC / "favicon.ico", media_type="image/x-icon")


@router.get("/favicon.svg")
def favicon_svg():
    return FileResponse(_STATIC / "favicon.svg", media_type="image/svg+xml")


@router.get("/apple-touch-icon.png")
def apple_touch_icon():
    return FileResponse(_STATIC / "apple-touch-icon.png", media_type="image/png")


@router.get("/icon-192.png")
def icon_192():
    return FileResponse(_STATIC / "icon-192.png", media_type="image/png")


@router.get("/icon-512.png")
def icon_512():
    return FileResponse(_STATIC / "icon-512.png", media_type="image/png")


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


@router.get("/login")
def login_page():
    return FileResponse(_STATIC / "html" / "dashboard.html")


@router.get("/forgot-password")
def forgot_password_page():
    return FileResponse(_STATIC / "html" / "forgot-password.html")


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