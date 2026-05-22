"""
Coordinator admin routes — invite, list, update course units, remove.
Refactor only; same paths and Supabase usage as before.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException

from app.dep import supabase_admin, check_admin, _bool_flag

router = APIRouter(tags=["admin-coordinators"])

APP_URL = os.getenv("APP_URL", "https://faceattend.app")


@router.post("/invite-coordinator")
async def invite_coordinator(
    full_name: str = Form(...),
    email: str = Form(...),
    institution_id: str = Form(default=None),
    course_unit_id: Optional[str] = Form(None),
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin = _bool_flag(profile.get("is_super_admin"))
    role = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super = is_super_admin or role == "super_admin"

    if is_super:
        if not institution_id or not institution_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Super admins must provide institution_id when inviting a coordinator.",
            )
        target_institution = institution_id.strip()
    else:
        if not user_institution:
            raise HTTPException(status_code=400, detail="Your admin account is not linked to an institution.")
        target_institution = user_institution

    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise HTTPException(status_code=400, detail="full_name cannot be empty.")
    if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    course_unit_id = course_unit_id.strip() if course_unit_id and course_unit_id.strip() else None

    try:
        auth_response = supabase_admin.auth.admin.invite_user_by_email(
            email,
            options={
                "data": {
                    "full_name": full_name,
                    "institution_id": target_institution,
                    "role": "coordinator",
                    "course_unit_id": course_unit_id,
                },
                "redirect_to": f"{APP_URL}/set-password",
            },
        )
        coordinator_user_id = auth_response.user.id
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(status_code=409, detail="This email is already registered.")
        raise HTTPException(status_code=500, detail=f"Invite failed: {error_msg}")

    try:
        profile_data = {
            "id": coordinator_user_id,
            "full_name": full_name,
            "institution_id": target_institution,
            "is_admin": False,
            "is_super_admin": False,
            "role": "coordinator",
        }
        if course_unit_id:
            profile_data["course_unit_id"] = [course_unit_id] if course_unit_id else None
        else:
            profile_data["course_unit_id"] = None
        supabase_admin.table("profiles").insert(profile_data).execute()
    except Exception as e:
        try:
            supabase_admin.auth.admin.delete_user(coordinator_user_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")

    return {
        "success": True,
        "coordinator_id": coordinator_user_id,
        "full_name": full_name,
        "email": email,
        "institution_id": target_institution,
        "course_unit_id": course_unit_id,
        "message": f"Invite sent to {email}. They will receive an email to set their password.",
    }


@router.get("/coordinators")
async def list_coordinators(
    institution_id: str = None,
    user=Depends(check_admin),
):
    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=403, detail="Admin profile not found.")

    is_super_admin = _bool_flag(profile.get("is_super_admin"))
    role = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super = is_super_admin or role == "super_admin"

    try:
        query = supabase_admin.table("profiles") \
            .select("id, full_name, role, institution_id, course_unit_id, created_at") \
            .eq("role", "coordinator") \
            .order("created_at", desc=True)

        if is_super:
            if institution_id:
                query = query.eq("institution_id", institution_id)
        else:
            if not user_institution:
                raise HTTPException(status_code=400, detail="Admin not linked to an institution.")
            query = query.eq("institution_id", user_institution)

        resp = query.execute()
        coordinators = resp.data or []
        return {"coordinators": coordinators, "count": len(coordinators)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

    is_super_admin = _bool_flag(profile.get("is_super_admin"))
    role = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super = is_super_admin or role == "super_admin"

    coord_resp = supabase_admin.table("profiles") \
        .select("institution_id, role") \
        .eq("id", coordinator_id).single().execute()
    coord = coord_resp.data
    if not coord:
        raise HTTPException(status_code=404, detail="Coordinator not found.")
    if coord.get("role") != "coordinator":
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
        "success": True,
        "coordinator_id": coordinator_id,
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

    is_super_admin = _bool_flag(profile.get("is_super_admin"))
    role = profile.get("role", "")
    user_institution = profile.get("institution_id")
    is_super = is_super_admin or role == "super_admin"

    coord_resp = supabase_admin.table("profiles") \
        .select("institution_id, role") \
        .eq("id", coordinator_id).limit(1).execute()

    coord = coord_resp.data[0] if coord_resp.data else None
    if not coord:
        raise HTTPException(status_code=404, detail="Coordinator not found.")
    if coord.get("role") != "coordinator":
        raise HTTPException(status_code=400, detail="Target user is not a coordinator.")

    if not is_super and coord.get("institution_id") != user_institution:
        raise HTTPException(status_code=403, detail="Coordinator does not belong to your institution.")

    try:
        supabase_admin.table("profiles").delete().eq("id", coordinator_id).execute()
        supabase_admin.auth.admin.delete_user(coordinator_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Removal failed: {str(e)}")

    return {
        "success": True,
        "removed_id": coordinator_id,
    }
