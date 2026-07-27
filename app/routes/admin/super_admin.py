"""Tiered super-admin access: aggregate overview and logged break-glass."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from supabase import create_client

from app.dep import SUPABASE_KEY, SUPABASE_URL, check_super_admin, supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/super", tags=["admin-super"])


class BreakGlassRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=8)


def _user_supabase(token: str):
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(token)
    return client


def _overview_fallback():
    """Mirror get_institution_overview() when RPC is not deployed yet."""
    insts = supabase_admin.table("institutions").select(
        "id, name, plan, status, trial_ends_at"
    ).execute().data or []

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    rows = []
    for inst in insts:
        inst_id = inst["id"]
        students = supabase_admin.table("students").select("id", count="exact") \
            .eq("institution_id", inst_id).execute().count or 0
        lecturers = supabase_admin.table("profiles").select("id", count="exact") \
            .eq("institution_id", inst_id).eq("role", "lecturer").execute().count or 0
        sessions = supabase_admin.table("sessions").select("id", count="exact") \
            .eq("institution_id", inst_id).gte("created_at", month_start).execute().count or 0
        rows.append({
            "institution_id": inst_id,
            "institution_name": inst.get("name") or inst_id,
            "active_students": students,
            "lecturers": lecturers,
            "sessions_this_month": sessions,
            "plan": inst.get("plan") or "free",
            "payment_status": inst.get("status") or "active",
            "trial_ends_at": inst.get("trial_ends_at"),
        })
    return rows


@router.get("/overview")
async def institution_overview(
    user=Depends(check_super_admin),
    authorization: str = Header(None),
):
    token = authorization.replace("Bearer ", "").strip() if authorization else ""
    try:
        result = _user_supabase(token).rpc("get_institution_overview").execute()
        if result.data is not None:
            return {"institutions": result.data}
    except Exception as exc:
        logger.warning("[super] get_institution_overview RPC failed, using fallback: %s", exc)

    return {"institutions": _overview_fallback(), "source": "fallback"}


@router.post("/break-glass")
async def break_glass_view(
    body: BreakGlassRequest,
    user=Depends(check_super_admin),
    authorization: str = Header(None),
):
    token = authorization.replace("Bearer ", "").strip() if authorization else ""
    try:
        result = _user_supabase(token).rpc(
            "break_glass_view_student",
            {"target_student_id": body.student_id.strip(), "reason": body.reason.strip()},
        ).execute()
        if result.data:
            row = result.data[0] if isinstance(result.data, list) else result.data
            return {"student": row}
    except Exception as exc:
        logger.warning("[super] break_glass_view_student RPC failed, using fallback: %s", exc)

    reason = body.reason.strip()
    if len(reason) < 8:
        raise HTTPException(status_code=400, detail="A specific reason (min 8 chars) is required")

    supabase_admin.table("audit_logs").insert({
        "actor_id": user.id,
        "action": "break_glass_access",
        "resource_type": "students",
        "resource_id": body.student_id.strip(),
        "metadata": {"reason": reason},
    }).execute()

    student_resp = supabase_admin.table("students").select("*") \
        .eq("id", body.student_id.strip()).limit(1).execute()
    if not student_resp.data:
        raise HTTPException(status_code=404, detail="Student not found")

    student = student_resp.data[0]
    attendance = supabase_admin.table("attendance_records").select("*") \
        .eq("student_id", body.student_id.strip()).execute().data or []

    return {
        "student": {
            "student_id": student.get("id"),
            "full_name": student.get("name"),
            "institution_id": student.get("institution_id"),
            "attendance_records": attendance,
        },
        "source": "fallback",
    }


@router.get("/security-summary")
async def security_summary(period_days: str = "all", user=Depends(check_super_admin)):
    """Per-institution spoof/failure counts — no student-level PII."""
    query = supabase_admin.table("attendance_records").select("institution_id, verified, timestamp")
    if period_days != "all":
        try:
            days = int(period_days)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("timestamp", cutoff)
        except ValueError:
            pass

    records = query.limit(10000).execute().data or []

    by_inst: dict[str, dict] = {}
    for r in records:
        inst_id = r.get("institution_id") or "Unknown"
        bucket = by_inst.setdefault(inst_id, {"spoof": 0, "failed": 0, "success": 0, "total": 0})
        bucket["total"] += 1
        verified = r.get("verified")
        if verified == "spoof":
            bucket["spoof"] += 1
        elif verified == "failed":
            bucket["failed"] += 1
        elif verified == "success":
            bucket["success"] += 1

    institutions = [
        {"institution_id": inst_id, **counts}
        for inst_id, counts in sorted(by_inst.items(), key=lambda x: x[1]["spoof"], reverse=True)
    ]
    return {"institutions": institutions}
