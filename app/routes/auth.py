"""
routes/auth_extra.py
Additional auth routes for FaceAttend:
  - POST /auth/forgot-password       → trigger Supabase password reset email
  - POST /auth/log-login             → Flutter fallback to log a login event
  - POST /webhooks/supabase-auth     → Supabase Auth webhook (primary login capture)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.dep import supabase, supabase_admin, verify_supabase_token, limiter
from app.utils.audit import AuditAction, log_event

logger = logging.getLogger(__name__)
router = APIRouter()

SUPABASE_WEBHOOK_SECRET = os.getenv("SUPABASE_WEBHOOK_SECRET", "")


def _audit_metadata(row: dict) -> dict:
    meta = row.get("metadata") or {}
    if isinstance(meta, str):
        try:
            import json
            meta = json.loads(meta)
        except Exception:
            meta = {}
    return meta if isinstance(meta, dict) else {}


def _has_recent_login(
    actor_id: str,
    *,
    source_filter: Optional[str] = None,
) -> bool:
    """
    Return True if auth.login was logged in the last 60 seconds.
    When source_filter is set (e.g. 'dashboard'), only matching sources count.
    """
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    try:
        recent = (
            supabase_admin.table("audit_logs")
            .select("id, metadata")
            .eq("actor_id", actor_id)
            .eq("action", AuditAction.AUTH_LOGIN)
            .gte("created_at", cutoff)
            .limit(10)
            .execute()
        )
        rows = recent.data or []
        if not rows:
            return False
        if source_filter is None:
            return True
        return any(
            _audit_metadata(row).get("source") == source_filter
            for row in rows
        )
    except Exception as exc:
        logger.error("[auth] Dedup check failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class LogLoginRequest(BaseModel):
    device_model: Optional[str] = None
    os_version:   Optional[str] = None
    app_version:  Optional[str] = None
    source:       Optional[str] = None

    class Config:
        extra = "allow"  # ← ignore unknown fields

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

class GooglePreflightRequest(BaseModel):
    id_token: str

@router.post("/auth/google-preflight")
@limiter.limit("10/minute")
async def google_preflight(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    body = GooglePreflightRequest(**payload)

    # Decode and verify the Google idToken
    try:
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID")
        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        email = id_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Could not extract email from token")
    except ValueError as e:
        logger.error("[google-preflight] Token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Check if email exists in profiles
    try:
        result = supabase_admin.table("profiles") \
            .select("id, role, institution_id") \
            .eq("email", email) \
            .limit(1) \
            .execute()
    except Exception as e:
        logger.error("[google-preflight] DB lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Server error")

    if not result.data:
        logger.warning("[google-preflight] No profile for email: %s", email)
        return {"allow": False, "reason": "No account found. Contact your institution admin."}

    role = result.data[0].get("role")
    flutter_allowed = ["central_admin", "dept_admin", "coordinator", "admin"]

    if role not in flutter_allowed:
        logger.warning("[google-preflight] Role %s not allowed in app", role)
        return {"allow": False, "reason": "Lecturers access FaceAttend at faceattend.app/dashboard"}

    return {"allow": True}


# ---------------------------------------------------------------------------
# POST /auth/forgot-password  (public — no JWT required)
# ---------------------------------------------------------------------------

@router.post("/auth/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(request: Request):
    # parse body manually — limiter interferes with automatic binding
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid or missing JSON body")
    
    body = ForgotPasswordRequest(**payload)
    
    try:
        supabase.auth.reset_password_for_email(
            body.email,
            options={"redirect_to": "https://faceattend.app/reset-password"},
        )
    except Exception as exc:
        logger.error("[forgot-password] Supabase error: %s", exc)
        return {"message": "If that email is registered, a reset link has been sent."}

    await log_event(
        AuditAction.AUTH_PASSWORD_RESET,
        actor_email=body.email,
        actor_id=None,
        institution_id=None,
        metadata={"note": "Password reset requested"},
        request=request,
    )

    return {"message": "If that email is registered, a reset link has been sent."}


# ---------------------------------------------------------------------------
# POST /auth/log-login  (JWT required — called by Flutter after signIn)
# ---------------------------------------------------------------------------

@router.post("/auth/log-login")
@limiter.limit("20/hour")
async def log_login(
    request: Request,
    current_user = Depends(verify_supabase_token),
):
    """
    Flutter/dashboard calls this after successful signIn.
    Fallback in case Supabase webhook missed the event.
    """
    try:
        raw = await request.json()
        body = LogLoginRequest(**raw)
    except Exception:
        body = LogLoginRequest()

    logger.info(f"[log-login] User: {current_user.id} | Source: {body.source}")

    actor_id    = current_user.id
    actor_email = current_user.email

    try:
        prof = supabase_admin.table("profiles").select("institution_id") \
            .eq("id", actor_id).limit(1).execute()
        institution_id = prof.data[0].get("institution_id") if prof.data else None
    except Exception as e:
        logger.error(f"[log-login] Profile lookup failed: {e}")
        institution_id = None

    # Dashboard logins only dedupe against other dashboard logs (not webhook/Flutter).
    dedup_source = "dashboard" if body.source == "dashboard" else None
    if _has_recent_login(actor_id, source_filter=dedup_source):
        logger.info(
            "[log-login] Skipping duplicate for %s (source=%s)",
            actor_id,
            body.source,
        )
        return {"message": "already logged"}

    await log_event(
        AuditAction.AUTH_LOGIN,
        actor_id=actor_id,
        actor_email=actor_email,
        institution_id=institution_id,
        metadata={
            "device_model": body.device_model,
            "os_version":   body.os_version,
            "app_version":  body.app_version,
            "source":       body.source,
        },
        request=request,
    )

    return {"message": "login logged"}

@router.post("/auth/log-logout")
async def log_logout(
    request: Request,
    current_user = Depends(verify_supabase_token),
):
    try:
        prof = supabase_admin.table("profiles").select("institution_id") \
            .eq("id", current_user.id).limit(1).execute()
        institution_id = prof.data[0].get("institution_id") if prof.data else None
    except Exception:
        institution_id = None

    await log_event(
        AuditAction.AUTH_LOGOUT,
        actor_id=current_user.id,
        actor_email=current_user.email,
        institution_id=institution_id,
        metadata={"source": request.headers.get("X-Source", "dashboard")},
        request=request,
    )
    return {"message": "logout logged"}


# ---------------------------------------------------------------------------
# POST /webhooks/supabase-auth  (called by Supabase Auth webhook)
# ---------------------------------------------------------------------------

def _verify_webhook_signature(payload_bytes: bytes, signature: Optional[str]) -> bool:
    """Verify Supabase webhook HMAC-SHA256 signature."""
    if not SUPABASE_WEBHOOK_SECRET:
        logger.warning("[webhook] SUPABASE_WEBHOOK_SECRET not set — skipping verification")
        return True  # allow in dev; set secret in prod
    if not signature:
        return False
    expected = hmac.new(
        SUPABASE_WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


@router.post("/webhooks/supabase-auth")
async def supabase_auth_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
):
    """
    Supabase Auth webhook — receives events when users log in, sign up, etc.
    Configure in Supabase Dashboard → Auth → Hooks.

    Supported event types: LOGIN, SIGNUP, PASSWORD_RECOVERY, TOKEN_REFRESHED
    """
    raw_body = await request.body()

    if not _verify_webhook_signature(raw_body, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("event", payload.get("type", "")).upper()
    user_data  = payload.get("user", payload.get("record", {})) or {}

    user_id    = user_data.get("id")
    user_email = user_data.get("email")

    if not user_id or not user_email:
        logger.warning("[webhook] Missing user_id or email in payload")
        return {"ok": True}

    logger.info("[webhook] Auth event: %s for %s", event_type, user_email)

    if event_type not in ("LOGIN", "SIGNUP"):
        return {"ok": True}  # ignore TOKEN_REFRESHED and other events

    # Look up profile for institution_id
    try:
        profile = (
            supabase.table("profiles")
            .select("id, institution_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        profile_data = profile.data[0] if profile.data else {}
        institution_id = profile_data.get("institution_id")
    except Exception as exc:
        logger.error("[webhook] Profile lookup failed: %s", exc)
        institution_id = None

    if _has_recent_login(user_id):
        logger.info("[webhook] Skipping duplicate login log for %s", user_id)
        return {"ok": True}

    await log_event(
        AuditAction.AUTH_LOGIN,
        actor_id=user_id,
        actor_email=user_email,
        institution_id=institution_id,
        metadata={"source": "supabase_webhook", "event_type": event_type},
        request=request,
    )

    return {"ok": True}
