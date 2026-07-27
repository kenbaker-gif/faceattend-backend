"""Auto-renewal management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.dep import supabase_admin, check_admin, _bool_flag

router = APIRouter(prefix="/admin/auto-renewal", tags=["admin-auto-renewal"])


def _check_institution_access(user, institution_id: str):
    p = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute().data or {}
    is_super = _bool_flag(p.get("is_super_admin")) or p.get("role") == "super_admin"
    if not is_super and p.get("institution_id") != institution_id:
        raise HTTPException(status_code=403, detail="Access denied")


def _require_central_admin(user, institution_id: str):
    p = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute().data or {}
    role = p.get("role", "")
    is_super = _bool_flag(p.get("is_super_admin")) or role == "super_admin"
    is_central = role == "central_admin"
    if not (is_super or is_central):
        raise HTTPException(status_code=403, detail="central_admin or super_admin required")
    if not is_super and p.get("institution_id") != institution_id:
        raise HTTPException(status_code=403, detail="Access denied")


class AutoRenewalToggle(BaseModel):
    institution_id: str
    enabled: bool
    payment_method: str = "pesapal"


@router.post("/toggle")
async def toggle_auto_renewal(request: AutoRenewalToggle, user=Depends(check_admin)):
    _require_central_admin(user, request.institution_id)

    inst = supabase_admin.table("institutions").select("*").eq("id", request.institution_id).execute()
    if not inst.data:
        raise HTTPException(404, "Institution not found")

    plan = inst.data[0].get("plan", "free")
    subscription_end = inst.data[0].get("subscription_end")

    if not subscription_end:
        raise HTTPException(400, "No active subscription")

    next_renewal = datetime.fromisoformat(subscription_end.replace('Z', '+00:00')) + timedelta(days=30)

    supabase_admin.table("auto_renewal_settings").upsert({
        "institution_id": request.institution_id,
        "enabled": request.enabled,
        "plan": plan,
        "payment_method": request.payment_method,
        "next_renewal_date": next_renewal.isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }).execute()

    return {
        "success": True,
        "enabled": request.enabled,
        "next_renewal_date": next_renewal.isoformat(),
        "plan": plan
    }


@router.get("/status/{institution_id}")
async def get_auto_renewal_status(institution_id: str, user=Depends(check_admin)):
    _check_institution_access(user, institution_id)

    result = supabase_admin.table("auto_renewal_settings").select("*") \
        .eq("institution_id", institution_id).execute()

    if not result.data:
        return {"enabled": False, "configured": False}

    s = result.data[0]
    return {
        "enabled": s["enabled"],
        "configured": True,
        "plan": s["plan"],
        "payment_method": s["payment_method"],
        "next_renewal_date": s["next_renewal_date"]
    }