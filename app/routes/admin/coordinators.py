"""
Coordinator admin routes — invite, list, update course units, remove.
Supports roles: coordinator, lecturer, dept_admin.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse

from app.dep import supabase_admin, check_admin, _bool_flag
from app.utils.email import send_generic_email

router = APIRouter(tags=["admin-coordinators"])

APP_URL = os.getenv("APP_URL", "https://faceattend.app")
LECTURER_CONFIRM_SECRET = os.getenv("LECTURER_CONFIRM_SECRET", os.getenv("ADMIN_SECRET", ""))
LECTURER_CONFIRM_TTL_SECONDS = int(os.getenv("LECTURER_CONFIRM_TTL", "86400"))


def _make_confirmation_token(session_id: str, lecturer_id: str, expires_at: str) -> str:
    payload = f"{session_id}|{lecturer_id}|{expires_at}"
    signature = hmac.new(
        LECTURER_CONFIRM_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()
    return token


def _parse_confirmation_token(token: str) -> tuple[str, str, str]:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        session_id, lecturer_id, expires_at, signature = decoded.split("|")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid confirmation token.")

    payload = f"{session_id}|{lecturer_id}|{expires_at}"
    expected = hmac.new(
        LECTURER_CONFIRM_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid confirmation token.")
    return session_id, lecturer_id, expires_at


def _ensure_confirm_secret() -> None:
    if not LECTURER_CONFIRM_SECRET:
        raise RuntimeError(
            "LECTURER_CONFIRM_SECRET must be set to generate and validate confirmation tokens."
        )


@router.post("/invite-coordinator")
async def invite_coordinator(
    full_name: str = Form(...),
    email: str = Form(...),
    institution_id: str = Form(default=None),
    course_unit_id: Optional[str] = Form(None),
    role: str = Form(default="coordinator"),
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    if is_super:
        if not institution_id or not institution_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Super admins must provide institution_id when inviting.",
            )
        target_institution = institution_id.strip()
    else:
        if not user_institution:
            raise HTTPException(status_code=400, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    full_name = full_name.strip()
    email     = email.strip().lower()

    if not full_name:
        raise HTTPException(status_code=400, detail="full_name cannot be empty.")
    if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    # ── Validate role ──────────────────────────────────────────────────────
    allowed_roles = {"coordinator", "lecturer", "dept_admin"}
    role = role.strip().lower() if role else "coordinator"
    if role not in allowed_roles:
        role = "coordinator"

    # course_unit_id is only stored on coordinator profiles.
    # Lecturers may be assigned to a course unit via the lecturer_courses table.
    course_unit_id = course_unit_id.strip() if course_unit_id and course_unit_id.strip() else None

    invited_user_id = None
    if role == "lecturer":
        existing_profile = supabase_admin.table("profiles") \
            .select("id") \
            .eq("email", email).limit(1).execute()
        if existing_profile.data:
            raise HTTPException(status_code=409, detail="This email is already registered.")

        random_password = base64.urlsafe_b64encode(os.urandom(18)).decode().rstrip("=")
        try:
            auth_response = supabase_admin.auth.admin.create_user({
                "email": email,
                "password": random_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": full_name,
                    "institution_id": target_institution,
                    "role": role,
                    "course_unit_id": course_unit_id,
                },
            })
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                raise HTTPException(status_code=409, detail="This email is already registered.")
            raise HTTPException(status_code=500, detail=f"Lecturer account creation failed: {error_msg}")

        invited_user_id = auth_response.user.id
        profile_data = {
            "id":             invited_user_id,
            "full_name":      full_name,
            "email":          email,
            "institution_id": target_institution,
            "is_admin":       False,
            "is_super_admin": False,
            "role":           role,
            "course_unit_id": None,
        }

        try:
            supabase_admin.table("profiles").insert(profile_data).execute()

            if course_unit_id:
                cu_resp = supabase_admin.table("course_units") \
                    .select("institution_id") \
                    .eq("id", course_unit_id).single().execute()
                if not cu_resp.data or cu_resp.data.get("institution_id") != target_institution:
                    raise HTTPException(
                        status_code=400,
                        detail="Course unit not found or does not belong to the institution.",
                    )

                existing = supabase_admin.table("lecturer_courses") \
                    .select("id") \
                    .eq("lecturer_id", invited_user_id) \
                    .eq("course_unit_id", course_unit_id) \
                    .limit(1).execute()
                if not existing.data:
                    supabase_admin.table("lecturer_courses").insert({
                        "lecturer_id": invited_user_id,
                        "course_unit_id": course_unit_id,
                        "institution_id": target_institution,
                    }).execute()
        except Exception as e:
            try:
                supabase_admin.auth.admin.delete_user(invited_user_id)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Lecturer profile creation failed: {str(e)}")

        try:
            email_html = f"""
              <h1>You've been added as a FaceAttend Lecturer</h1>
              <p>Hi {full_name},</p>
              <p>You have been added to FaceAttend as a lecturer for institution <strong>{target_institution}</strong>.</p>
              <p>When a coordinator starts an attendance session, you will be asked to confirm that you taught the class.</p>
              <p>No password is required for this role at this time.</p>
              <p>If this was not expected, please contact your institution administrator.</p>
            """
            await send_generic_email([email], 'FaceAttend Lecturer Assignment', email_html)
        except Exception as email_err:
            print(f"Warning: failed to send lecturer email to {email}: {email_err}")

        return {
            "success":        True,
            "invited_id":     invited_user_id,
            "full_name":      full_name,
            "email":          email,
            "institution_id": target_institution,
            "role":           role,
            "course_unit_id": course_unit_id,
            "message":        f"Lecturer record created for {email}. They do not need a password.",
        }

    try:
        auth_response = supabase_admin.auth.admin.invite_user_by_email(
            email,
            options={
                "data": {
                    "full_name":      full_name,
                    "institution_id": target_institution,
                    "role":           role,
                    "course_unit_id": course_unit_id,
                },
                # Include a query parameter so the invite redirect preserves intent
                "redirect_to": f"{APP_URL}/set-password?source=invite",
            },
        )
        invited_user_id = auth_response.user.id
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(status_code=409, detail="This email is already registered.")
        raise HTTPException(status_code=500, detail=f"Invite failed: {error_msg}")

    try:
        profile_data = {
            "id":             invited_user_id,
            "full_name":      full_name,
            "institution_id": target_institution,
            "is_admin":       False,
            "is_super_admin": False,
            "role":           role,
        }

        # Only set course_unit_id array for coordinators
        if role == "coordinator":
            profile_data["course_unit_id"] = [course_unit_id] if course_unit_id else None
        else:
            profile_data["course_unit_id"] = None

        supabase_admin.table("profiles").insert(profile_data).execute()

        # If a lecturer invite includes a course unit, assign them immediately.
        if role == "lecturer" and course_unit_id:
            cu_resp = supabase_admin.table("course_units") \
                .select("institution_id") \
                .eq("id", course_unit_id).single().execute()
            if not cu_resp.data or cu_resp.data.get("institution_id") != target_institution:
                raise HTTPException(
                    status_code=400,
                    detail="Course unit not found or does not belong to the institution.",
                )

            existing = supabase_admin.table("lecturer_courses") \
                .select("id") \
                .eq("lecturer_id", invited_user_id) \
                .eq("course_unit_id", course_unit_id) \
                .limit(1).execute()
            if not existing.data:
                supabase_admin.table("lecturer_courses").insert({
                    "lecturer_id": invited_user_id,
                    "course_unit_id": course_unit_id,
                    "institution_id": target_institution,
                }).execute()
    except Exception as e:
        # Roll back auth user if profile insert fails
        try:
            supabase_admin.auth.admin.delete_user(invited_user_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")

    return {
        "success":        True,
        "invited_id":     invited_user_id,
        "full_name":      full_name,
        "email":          email,
        "institution_id": target_institution,
        "role":           role,
        "course_unit_id": course_unit_id,
        "message":        f"Invite sent to {email}. They will receive an email to set their password.",
    }


@router.post("/resend-invite")
async def resend_invite(
    email: str = Form(...),
    institution_id: Optional[str] = Form(None),
    role: str = Form(default="lecturer"),
    user=Depends(check_admin),
):
    """Resend an invite email to an existing or new user. Requires admin."""
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    if is_super:
        if institution_id and institution_id.strip():
            target_institution = institution_id.strip()
        else:
            raise HTTPException(status_code=400, detail="Super admins must provide institution_id.")
    else:
        if not user_institution:
            raise HTTPException(status_code=400, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    if role == "lecturer":
        raise HTTPException(
            status_code=400,
            detail="Lecturers do not receive a login invite. Use the lecturer confirmation flow instead.",
        )

    try:
        auth_response = supabase_admin.auth.admin.invite_user_by_email(
            email,
            options={
                "data": {"institution_id": target_institution, "role": role},
                "redirect_to": f"{APP_URL}/set-password?source=invite",
            },
        )
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            # If user exists, just return success so frontend can inform the admin
            return {"success": True, "message": "User already registered; invite email resent if possible."}
        raise HTTPException(status_code=500, detail=f"Resend invite failed: {error_msg}")

    return {"success": True, "message": f"Invite resent to {email}."}


@router.post("/lecturer/send-confirmation-link")
async def send_lecturer_confirmation_link(
    session_id: str = Form(...),
    lecturer_id: str = Form(...),
    user=Depends(check_admin),
):
    """Send a one-click confirmation link to a lecturer for a specific session."""
    _ensure_confirm_secret()

    profile_resp = supabase_admin.table("profiles") \
        .select("email, full_name") \
        .eq("id", lecturer_id).single().execute()
    profile = profile_resp.data
    if not profile or not profile.get("email"):
        raise HTTPException(status_code=404, detail="Lecturer profile not found.")

    session_resp = supabase_admin.table("sessions") \
        .select("id, lecturer_id, institution_id, status") \
        .eq("id", session_id).single().execute()
    session_data = session_resp.data
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session_data.get("lecturer_id") != lecturer_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this lecturer.")

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=LECTURER_CONFIRM_TTL_SECONDS)).isoformat()
    token = _make_confirmation_token(session_id, lecturer_id, expires_at)
    confirmation_url = f"{APP_URL}/lecturer/confirm-session?token={quote(token)}"

    email_html = f"""
      <h1>Confirm your FaceAttend session</h1>
      <p>Hi {profile.get('full_name') or 'Lecturer'},</p>
      <p>A coordinator has created a session for which you are the assigned lecturer.</p>
      <p>Click the button below to confirm that you taught this session:</p>
      <p><a href=\"{confirmation_url}\" style=\"padding:12px 18px;background:#10B981;color:#ffffff;text-decoration:none;border-radius:8px;\">Confirm Session</a></p>
      <p>This link will expire in {LECTURER_CONFIRM_TTL_SECONDS // 3600} hour(s).</p>
      <p>If you did not expect this, please contact your administrator.</p>
    """

    try:
        await send_generic_email(
            [profile["email"]],
            "Confirm your FaceAttend session",
            email_html,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send confirmation email: {exc}")

    return {
        "success": True,
        "message": f"Confirmation link sent to {profile['email']}",
        "confirmation_url": confirmation_url,
    }


@router.get("/lecturer/confirm-session")
async def lecturer_confirm_session(token: str):
    """Confirm a lecturer session by token link."""
    _ensure_confirm_secret()

    session_id, lecturer_id, expires_at = _parse_confirmation_token(token)
    expires_dt = datetime.fromisoformat(expires_at)
    if expires_dt < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Confirmation link has expired.")

    session_resp = supabase_admin.table("sessions") \
        .select("id, lecturer_id, status, lecturer_confirmed") \
        .eq("id", session_id).single().execute()
    session_data = session_resp.data
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session_data.get("lecturer_id") != lecturer_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this lecturer.")

    if session_data.get("lecturer_confirmed"):
        return HTMLResponse(
            "<h1>Session already confirmed</h1><p>This session has already been confirmed.</p>",
            status_code=200,
        )

    update_resp = supabase_admin.table("sessions").update({
        "status": "confirmed",
        "lecturer_confirmed": True,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute()
    if update_resp.error:
        raise HTTPException(status_code=500, detail=f"Failed to confirm session: {update_resp.error.message}")

    return HTMLResponse(
        "<h1>Session confirmed</h1><p>Thank you — the session has been confirmed.</p>",
        status_code=200,
    )


@router.get("/coordinators")
async def list_coordinators(
    institution_id: Optional[str] = None,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    target_institution = None
    if institution_id:
        if not is_super and institution_id != user_institution:
            raise HTTPException(status_code=403, detail="Permission denied.")
        target_institution = institution_id
    elif not is_super:
        if not user_institution:
            raise HTTPException(
                status_code=403,
                detail="Your admin account is not linked to an institution.",
            )
        target_institution = user_institution

    query = supabase_admin.table("profiles") \
        .select("id, full_name, email, created_at, institution_id, course_unit_id, role") \
        .eq("role", "coordinator")
    if target_institution:
        query = query.eq("institution_id", target_institution)
    query = query.order("created_at", desc=True)

    resp = query.execute()
    coordinators = resp.data or []

    return {"coordinators": coordinators}


@router.get("/lecturers")
async def list_lecturers(
    institution_id: Optional[str] = None,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    target_institution = None
    if institution_id:
        if not is_super and institution_id != user_institution:
            raise HTTPException(status_code=403, detail="Permission denied.")
        target_institution = institution_id
    elif not is_super:
        if not user_institution:
            raise HTTPException(
                status_code=403,
                detail="Your admin account is not linked to an institution.",
            )
        target_institution = user_institution

    query = supabase_admin.table("profiles") \
        .select("id, full_name, email, created_at, institution_id, role") \
        .eq("role", "lecturer")

    if target_institution:
        query = query.eq("institution_id", target_institution)

    query = query.order("created_at", desc=True)
    resp = query.execute()
    lecturers = resp.data or []

    return {"lecturers": lecturers}


@router.get("/dept-admins")
async def list_dept_admins(
    institution_id: Optional[str] = None,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    target_institution = None
    if institution_id:
        if not is_super and institution_id != user_institution:
            raise HTTPException(status_code=403, detail="Permission denied.")
        target_institution = institution_id
    elif not is_super:
        if not user_institution:
            raise HTTPException(status_code=403, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    query = supabase_admin.table("profiles") \
        .select("id, full_name, email, created_at, institution_id, department_id, role") \
        .in_("role", ["dept_admin"])

    if target_institution:
        query = query.eq("institution_id", target_institution)

    query = query.order("created_at", desc=True)
    resp  = query.execute()

    return {"dept_admins": resp.data or []}


@router.post("/lecturer/confirm-session")
async def confirm_lecturer_session(
    session_id: str = Form(...),
    lecturer_id: str = Form(...),
    lecturer_email: Optional[str] = Form(None),
):
    """Confirm a session on behalf of a lecturer via email link or external workflow."""
    if not session_id or not lecturer_id:
        raise HTTPException(status_code=400, detail="session_id and lecturer_id are required.")

    if lecturer_email:
        profile_resp = supabase_admin.table("profiles") \
            .select("email") \
            .eq("id", lecturer_id).single().execute()
        profile_data = profile_resp.data
        if not profile_data or not profile_data.get("email"):
            raise HTTPException(status_code=404, detail="Lecturer profile not found.")
        if profile_data.get("email", "").strip().lower() != lecturer_email.strip().lower():
            raise HTTPException(status_code=403, detail="Lecturer email does not match.")

    session_resp = supabase_admin.table("sessions") \
        .select("id, lecturer_id, status") \
        .eq("id", session_id).single().execute()
    session_data = session_resp.data
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session_data.get("lecturer_id") != lecturer_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this lecturer.")

    update_resp = supabase_admin.table("sessions").update({
        "status": "confirmed",
        "lecturer_confirmed": True,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute()

    if update_resp.error:
        raise HTTPException(status_code=500, detail=f"Failed to confirm session: {update_resp.error.message}")

    return {
        "success": True,
        "session_id": session_id,
        "message": "Session confirmed by lecturer.",
    }


@router.post("/admin/lecturer-courses")
async def assign_lecturer_course(
    lecturer_id: str = Form(...),
    course_unit_id: str = Form(...),
    institution_id: Optional[str] = Form(None),
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    if is_super:
        # Allow super admins to act on their own institution when no institution_id
        # is provided (tests and some admin flows expect this behavior).
        if not institution_id or not institution_id.strip():
            if user_institution:
                target_institution = user_institution
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Super admins must provide institution_id when assigning a lecturer.",
                )
        else:
            target_institution = institution_id.strip()
    else:
        if not user_institution:
            raise HTTPException(status_code=400, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    lecturer_resp = supabase_admin.table("profiles") \
        .select("institution_id, role") \
        .eq("id", lecturer_id).single().execute()
    lecturer = lecturer_resp.data
    if not lecturer or lecturer.get("role") != "lecturer":
        raise HTTPException(status_code=404, detail="Lecturer not found.")
    if lecturer.get("institution_id") != target_institution:
        raise HTTPException(
            status_code=403,
            detail="Lecturer does not belong to the target institution.",
        )

    cu_resp = supabase_admin.table("course_units") \
        .select("institution_id") \
        .eq("id", course_unit_id).single().execute()
    if not cu_resp.data or cu_resp.data.get("institution_id") != target_institution:
        raise HTTPException(
            status_code=404,
            detail="Course unit not found or does not belong to the institution.",
        )

    existing = supabase_admin.table("lecturer_courses") \
        .select("id") \
        .eq("lecturer_id", lecturer_id) \
        .eq("course_unit_id", course_unit_id) \
        .limit(1).execute()

    if existing.data:
        return {
            "success":      True,
            "assigned":     False,
            "assignment_id": existing.data[0]["id"],
            "message":      "Lecturer is already assigned to this course unit.",
        }

    assignment_resp = supabase_admin.table("lecturer_courses").insert({
        "lecturer_id": lecturer_id,
        "course_unit_id": course_unit_id,
        "institution_id": target_institution,
    })

    # Support both client libraries that return a query-like object with
    # `.execute()` and test/mocks that return a result-like object directly.
    try:
        if hasattr(assignment_resp, "execute"):
            assignment_resp = assignment_resp.execute()
    except Exception:
        # If the mocked insert raises, surface as server error
        raise HTTPException(status_code=500, detail="Failed to assign lecturer to course unit.")

    if not getattr(assignment_resp, "data", None):
        raise HTTPException(status_code=500, detail="Failed to assign lecturer to course unit.")

    return {
        "success":      True,
        "assigned":     True,
        "assignment_id": assignment_resp.data[0]["id"],
        "message":      "Lecturer assigned to course unit successfully.",
    }


@router.delete("/admin/lecturer-courses")
async def unassign_lecturer_course(
    lecturer_id: str,
    course_unit_id: str,
    institution_id: Optional[str] = None,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    if is_super:
        # Allow super admins to act on their own institution when no institution_id
        # is provided (tests and some admin flows expect this behavior).
        if not institution_id or not institution_id.strip():
            if user_institution:
                target_institution = user_institution
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Super admins must provide institution_id when unassigning a lecturer.",
                )
        else:
            target_institution = institution_id.strip()
    else:
        if not user_institution:
            raise HTTPException(status_code=400, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    lecturer_resp = supabase_admin.table("profiles") \
        .select("institution_id, role") \
        .eq("id", lecturer_id).single().execute()
    lecturer = lecturer_resp.data
    if not lecturer or lecturer.get("role") != "lecturer":
        raise HTTPException(status_code=404, detail="Lecturer not found.")
    if lecturer.get("institution_id") != target_institution:
        raise HTTPException(
            status_code=403,
            detail="Lecturer does not belong to the target institution.",
        )

    cu_resp = supabase_admin.table("course_units") \
        .select("institution_id") \
        .eq("id", course_unit_id).single().execute()
    if not cu_resp.data or cu_resp.data.get("institution_id") != target_institution:
        raise HTTPException(
            status_code=404,
            detail="Course unit not found or does not belong to the institution.",
        )

    delete_resp = supabase_admin.table("lecturer_courses") \
        .delete() \
        .eq("lecturer_id", lecturer_id) \
        .eq("course_unit_id", course_unit_id) \
        .eq("institution_id", target_institution).execute()

    deleted = bool(getattr(delete_resp, "count", None) or (delete_resp.data and len(delete_resp.data) > 0))
    if not deleted:
        return {
            "success":    True,
            "unassigned": False,
            "message":    "No lecturer assignment was found for that course unit.",
        }

    return {
        "success":    True,
        "unassigned": True,
        "message":    "Lecturer unassigned from course unit successfully.",
    }


@router.patch("/admin/coordinators/{coordinator_id}/course-unit")
async def update_coordinator_course_unit(
    coordinator_id: str,
    course_unit_ids: Optional[str] = Form(None),
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    role             = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or role == "super_admin"

    coord_resp = supabase_admin.table("profiles") \
        .select("institution_id, role") \
        .eq("id", coordinator_id).single().execute()
    coord = coord_resp.data
    if not coord:
        raise HTTPException(status_code=404, detail="Coordinator not found.")

    # ── Fixed: allow coordinator and dept_admin ────────────────────────────
    if coord.get("role") not in {"coordinator", "dept_admin"}:
        raise HTTPException(status_code=400, detail="Target user is not a coordinator.")

    if not is_super and coord.get("institution_id") != user_institution:
        raise HTTPException(status_code=403, detail="Coordinator does not belong to your institution.")

    course_unit_id_list = []
    if course_unit_ids and course_unit_ids.strip():
        course_unit_id_list = [id.strip() for id in course_unit_ids.split(',') if id.strip()]

    for course_unit_id in course_unit_id_list:
        unit_resp = supabase_admin.table("course_units") \
            .select("id, institution_id") \
            .eq("id", course_unit_id).single().execute()
        unit = unit_resp.data
        if not unit:
            raise HTTPException(status_code=404, detail=f"Course unit {course_unit_id} not found.")
        if not is_super and unit.get("institution_id") != user_institution:
            raise HTTPException(
                status_code=403,
                detail=f"Course unit {course_unit_id} does not belong to your institution.",
            )

    try:
        update_resp = supabase_admin.table("profiles") \
            .update({"course_unit_id": course_unit_id_list if course_unit_id_list else None}) \
            .eq("id", coordinator_id).execute()
    except Exception as e:
        error_detail = str(e)
        print(f"[update_coordinator_course_unit] update failed: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

    if not update_resp.data:
        error_detail = "No data returned from update operation"
        print(f"[update_coordinator_course_unit] {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

    return {
        "success":         True,
        "coordinator_id":  coordinator_id,
        "course_unit_ids": course_unit_id_list,
    }


@router.delete("/coordinators/{coordinator_id}")
async def remove_coordinator(
    coordinator_id: str,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    role             = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or role == "super_admin"

    coord_resp = supabase_admin.table("profiles") \
        .select("institution_id, role") \
        .eq("id", coordinator_id).limit(1).execute()

    coord = coord_resp.data[0] if coord_resp.data else None
    if not coord:
        raise HTTPException(status_code=404, detail="User not found.")

    # ── Fixed: allow removing coordinator, lecturer, dept_admin ───────────
    removable_roles = {"coordinator", "lecturer", "dept_admin"}
    if coord.get("role") not in removable_roles:
        raise HTTPException(status_code=400, detail="Target user cannot be removed via this endpoint.")

    if not is_super and coord.get("institution_id") != user_institution:
        raise HTTPException(status_code=403, detail="User does not belong to your institution.")

    try:
        # ── Fixed: clean up lecturer_courses before deleting profile ──────
        try:
            supabase_admin.table("lecturer_courses") \
                .delete().eq("lecturer_id", coordinator_id).execute()
        except Exception:
            pass  # non-critical, don't block removal

        supabase_admin.table("profiles").delete().eq("id", coordinator_id).execute()
        supabase_admin.auth.admin.delete_user(coordinator_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Removal failed: {str(e)}")

    return {
        "success":    True,
        "removed_id": coordinator_id,
    }



@router.get("/departments")
async def list_departments(
    institution_id: Optional[str] = None,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    target_institution = None
    if institution_id:
        if not is_super and institution_id != user_institution:
            raise HTTPException(status_code=403, detail="Permission denied.")
        target_institution = institution_id
    elif not is_super:
        if not user_institution:
            raise HTTPException(status_code=403, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    query = supabase_admin.table("departments") \
        .select("id, name, created_at, institution_id")

    if target_institution:
        query = query.eq("institution_id", target_institution)

    query = query.order("created_at", desc=False)
    resp  = query.execute()

    return {"departments": resp.data or []}


@router.post("/departments")
async def create_department(
    name: str = Form(...),
    institution_id: Optional[str] = Form(None),
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    if is_super:
        if not institution_id or not institution_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Super admins must provide institution_id when creating a department.",
            )
        target_institution = institution_id.strip()
    else:
        if not user_institution:
            raise HTTPException(status_code=400, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Department name cannot be empty.")

    try:
        insert_resp = supabase_admin.table("departments").insert({
            "name": name,
            "institution_id": target_institution,
        }).execute()

        if not insert_resp.data:
            raise HTTPException(status_code=500, detail="Failed to create department.")

        return {
            "success": True,
            "department": insert_resp.data[0],
            "message": f"Department '{name}' created successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create department: {str(e)}")


@router.delete("/departments/{department_id}")
async def delete_department(
    department_id: str,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin   = _bool_flag(profile.get("is_super_admin"))
    admin_role       = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super         = is_super_admin or admin_role == "super_admin"

    dept_resp = supabase_admin.table("departments") \
        .select("institution_id, name") \
        .eq("id", department_id).single().execute()

    dept = dept_resp.data
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    if not is_super and dept.get("institution_id") != user_institution:
        raise HTTPException(status_code=403, detail="Department does not belong to your institution.")

    try:
        supabase_admin.table("departments").delete().eq("id", department_id).execute()
        return {
            "success": True,
            "deleted_id": department_id,
            "message": f"Department '{dept.get('name')}' deleted successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete department: {str(e)}")
