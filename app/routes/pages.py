"""
Static HTML pages and public redirects served by FastAPI.
"""

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

router = APIRouter(tags=["pages"])

_STATIC = "static"
app.mount("/static", StaticFiles(directory="static"), name="static")

@router.get("/")
def home():
    return FileResponse(os.path.join(_STATIC, "index.html"))


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/set-password")
def set_password_page():
    return FileResponse(os.path.join(_STATIC, "set-password.html"))


@router.get("/reset-password")
def reset_password_page():
    return FileResponse(os.path.join(_STATIC, "reset-password.html"))


@router.get("/dashboard")
def dashboard_page():
    return FileResponse(os.path.join(_STATIC, "dashboard.html"))


@router.get("/privacy")
def privacy_page():
    return FileResponse(os.path.join(_STATIC, "privacy.html"))


@router.get("/terms")
def terms_page():
    return FileResponse(os.path.join(_STATIC, "terms.html"))

@router.get("/styles.css")
def styles():
    return FileResponse(os.path.join(_STATIC, "styles.css"), media_type="text/css")

@router.get("/main.js")
def main_js():
    return FileResponse(os.path.join(_STATIC, "main.js"), media_type="application/javascript")


@router.get("/download/faceattend.apk")
async def download_apk():
    return RedirectResponse(
        url="https://github.com/kenbaker-gif/Smart_attendance_app/releases/latest/download/app-release.apk",
    )
