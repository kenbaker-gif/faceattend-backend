"""
Institution routes — public registration, admin list/status, trial check.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.dep import supabase_admin, check_admin, check_super_admin, _bool_flag

router = APIRouter(tags=["admin-institutions"])

APP_URL = os.getenv("APP_URL", "https://faceattend.app")

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "aol.com", "protonmail.com",
    "zoho.com", "ymail.com", "mail.com", "googlemail.com",
}

PAID_PLANS = {"starter", "growth", "pro", "enterprise"}


def generate_institution_id(name: str) -> str:
    words = name.strip().upper().split()
    stop = {"OF", "THE", "AND", "FOR", "A", "AN", "IN", "AT", "TO"}
    words = [w for w in words if w not in stop]
    if len(words) >= 3:
        code = "".join(w[0] for w in words[:3])
    elif len(words) == 2:
        code = words[0][:2] + words[1][0]
    else:
        code = words[0][:3]
    return re.sub(r'[^A-Z0-9]', '', code)[:5]


@router.post("/register-institution")
async def register_institution(
    university_name: str = Form(...),
    admin_full_name: str = Form(...),
    admin_email: str = Form(...),
    phone: str = Form(...),
    logo: UploadFile = File(None),
):
    if not all([university_name.strip(), admin_full_name.strip(),
                admin_email.strip(), phone.strip()]):
        raise HTTPException(status_code=400, detail="All fields are required.")

    email = admin_email.strip().lower()
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    domain = email.split("@")[-1]
    if domain in FREE_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Please use your official institutional email address. Personal emails (Gmail, Yahoo, etc.) are not accepted.",
        )

    base_id = generate_institution_id(university_name)
    inst_id = base_id
    existing = supabase_admin.table("institutions").select("id").execute().data
    existing_ids = {r["id"] for r in existing}
    counter = 1
    while inst_id in existing_ids:
        inst_id = f"{base_id}{counter}"
        counter += 1

    logo_url = None
    if logo and logo.filename:
        logo_bytes = await logo.read()
        if len(logo_bytes) > 0:
            logo_path = f"logos/{inst_id}.png"
            try:
                supabase_admin.storage.from_("raw_faces").remove([logo_path])
            except Exception as e:
                print(f"Warning: Failed to remove old logo {logo_path}: {e}")
            supabase_admin.storage.from_("raw_faces").upload(
                logo_path, logo_bytes,
                file_options={"content-type": logo.content_type or "image/png"},
            )
            logo_url = supabase_admin.storage.from_("raw_faces").get_public_url(logo_path)

    try:
        supabase_admin.table("institutions").insert({
            "id": inst_id,
            "name": university_name.strip(),
            "plans": "trial",
            "is_active": True,
            "status": "pending",
            "admin_email": email,
            "phone": phone.strip(),
            "logo_url": logo_url,
            "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Institution creation failed: {str(e)}")

    try:
        auth_response = supabase_admin.auth.admin.invite_user_by_email(
            email,
            options={
                "data": {
                    "full_name": admin_full_name.strip(),
                    "institution_id": inst_id,
                },
                "redirect_to": f"{APP_URL}/set-password",
            },
        )
        user_id = auth_response.user.id
    except Exception as e:
        try:
            supabase_admin.table("institutions").delete().eq("id", inst_id).execute()
        except Exception as e:
            print(f"Warning: Failed to delete institution {inst_id}: {e}")
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Email already registered.")
        raise HTTPException(status_code=500, detail=f"Auth error: {error_msg}")

    try:
        supabase_admin.table("profiles").insert({
            "id": user_id,
            "is_admin": True,
            "institution_id": inst_id,
            "role": "admin",
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")

    return {
        "success": True,
        "institution_id": inst_id,
        "institution_name": university_name.strip(),
        "message": f"Registration received. Check {email} to set your password. Your account will be activated after review.",
        "trial_days": 30,
    }


@router.patch("/admin/institutions/{institution_id}/status")
async def update_institution_status(
    institution_id: str,
    status: str = Form(...),
    user=Depends(check_super_admin),
):
    if status not in ("pending", "active", "suspended"):
        raise HTTPException(status_code=400, detail="status must be one of: pending, active, suspended")
    try:
        resp = supabase_admin.table("institutions") \
            .update({"status": status}) \
            .eq("id", institution_id) \
            .execute()
        if not resp.data:
            raise HTTPException(status_code=404, detail="Institution not found.")
        return {
            "success": True,
            "institution_id": institution_id,
            "status": status,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/institutions")
async def list_institutions(
    status: str = None,
    user=Depends(check_admin),
):
    try:
        profile_resp = supabase_admin.table("profiles") \
            .select("institution_id, is_super_admin, role") \
            .eq("id", user.id).single().execute()

        if not profile_resp.data:
            raise HTTPException(status_code=403, detail="Admin profile not found")

        is_super_admin = _bool_flag(profile_resp.data.get("is_super_admin"))
        role = profile_resp.data.get("role", "")
        institution_id = profile_resp.data.get("institution_id")
        is_super = is_super_admin or role == "super_admin"

        if is_super:
            query = supabase_admin.table("institutions") \
                .select("id, name, admin_email, phone, plans, status, is_active, logo_url") \
                .order("name")
            if status:
                query = query.eq("status", status)
        else:
            if not institution_id:
                raise HTTPException(status_code=403, detail="Institution admin requires institution_id in profile")
            query = supabase_admin.table("institutions") \
                .select("id, name, admin_email, phone, plans, status, is_active, logo_url") \
                .eq("id", institution_id)

        resp = query.execute()
        institutions = resp.data or []
        return {"institutions": institutions, "count": len(institutions)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /admin/institutions failed: {repr(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/check-trial/{institution_id}")
def check_trial(institution_id: str):
    try:
        resp = supabase_admin.table("institutions") \
            .select("plans, is_active, trial_ends_at, name, status") \
            .eq("id", institution_id) \
            .limit(1).execute()
        if not resp.data:
            raise HTTPException(status_code=404, detail="Institution not found.")
        inst = resp.data[0]

        status = inst.get("status", "active")
        if status == "pending":
            return {"active": False, "reason": "Institution pending approval."}
        if status == "suspended":
            return {"active": False, "reason": "Account suspended."}

        trial_ends = inst.get("trial_ends_at")
        is_active = inst.get("is_active", False)
        plans = inst.get("plans", "trial")

        if not is_active:
            return {"active": False, "reason": "Account suspended."}

        # Paid plan — always active regardless of trial_ends_at
        if plans in PAID_PLANS:
            return {"active": True, "plans": plans}

        # Trial plan — check expiry
        if trial_ends:
            ends_at = datetime.fromisoformat(trial_ends.replace("Z", "+00:00"))
            days_left = (ends_at - datetime.now(timezone.utc)).days
            if days_left <= 0:
                return {"active": False, "reason": "Trial expired.", "days_left": 0}
            return {"active": True, "plans": "trial", "days_left": days_left}

        return {"active": True, "plans": plans}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))