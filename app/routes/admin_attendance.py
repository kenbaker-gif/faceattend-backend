"""
Admin attendance routes: records, summary, AI report.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.dep import supabase_admin, check_admin, _bool_flag, limiter
from app.utils.audit import AuditAction, log_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-attendance"])

APP_URL = os.getenv("APP_URL", "https://faceattend.app")
AI_RECORD_LIMIT = int(os.getenv("AI_SUMMARY_RECORD_LIMIT", "1000"))
AI_AT_RISK_PCT = float(os.getenv("AI_AT_RISK_PCT", "75"))
AI_MIN_SESSIONS = int(os.getenv("AI_MIN_SESSIONS", "3"))
AI_SUMMARY_MODEL = os.getenv("AI_SUMMARY_MODEL", "deepseek/deepseek-chat")
VALID_SCOPES = frozenset({"institution", "course_unit", "student"})


@router.get("/admin/attendance-records")
async def get_attendance_records(
    institution_id: str = None,
    limit: int = 500,
    user=Depends(check_admin),
):
    try:
        profile_resp = supabase_admin.table("profiles") \
            .select("institution_id, is_super_admin, role") \
            .eq("id", user.id).single().execute()

        is_super_admin = _bool_flag(profile_resp.data.get("is_super_admin") if profile_resp.data else None)
        role           = profile_resp.data.get("role", "") if profile_resp.data else ""
        user_institution_id = profile_resp.data.get("institution_id") if profile_resp.data else None

        is_super = is_super_admin or role == "super_admin"

        if not is_super and not user_institution_id:
            raise HTTPException(status_code=403, detail="Institution admin requires institution_id in profile")

        query = supabase_admin.table("attendance_records") \
            .select("*, course_units(name)") \
            .order("timestamp", desc=True) \
            .limit(limit)

        if is_super:
            if institution_id:
                query = query.eq("institution_id", institution_id)
        else:
            query = query.eq("institution_id", user_institution_id)

        rows = query.execute().data or []

        for row in rows:
            cu = row.pop("course_units", None)
            row["course_unit_name"] = cu["name"] if cu else "N/A"

        return rows
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/ai-attendance-summary")
@limiter.limit("10/hour")
async def ai_attendance_summary(
    request: Request,
    scope: str = "institution",
    scope_id: str = None,
    date_from: str = None,
    date_to: str = None,
    institution_id: str = None,
    user=Depends(check_admin),
):
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not configured.")

    scope = (scope or "institution").strip().lower()
    if scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope. Use one of: {', '.join(sorted(VALID_SCOPES))}.",
        )
    if scope in ("course_unit", "student") and not scope_id:
        raise HTTPException(status_code=400, detail=f"scope_id is required when scope is {scope}.")

    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data or {}
    is_super = _bool_flag(profile.get("is_super_admin")) or profile.get("role", "") == "super_admin"
    user_institution_id = profile.get("institution_id")

    if not is_super and not user_institution_id:
        raise HTTPException(status_code=403, detail="Admin not linked to an institution.")

    if is_super:
        effective_institution_id = institution_id or user_institution_id
        if not effective_institution_id:
            raise HTTPException(
                status_code=400,
                detail="Super admin must pass institution_id for AI summary.",
            )
    else:
        effective_institution_id = user_institution_id

    institution_name = effective_institution_id
    inst_resp = supabase_admin.table("institutions") \
        .select("name") \
        .eq("id", effective_institution_id).limit(1).execute()
    if inst_resp.data:
        institution_name = inst_resp.data[0]["name"]

    course_unit_name = None
    if scope == "course_unit" and scope_id:
        cu_resp = supabase_admin.table("course_units") \
            .select("name") \
            .eq("id", scope_id).limit(1).execute()
        course_unit_name = cu_resp.data[0]["name"] if cu_resp.data else scope_id

    try:
        query = supabase_admin.table("attendance_records") \
            .select("student_id, verified, timestamp, course_unit_id") \
            .eq("institution_id", effective_institution_id) \
            .order("timestamp", desc=True) \
            .limit(AI_RECORD_LIMIT)

        if scope == "course_unit":
            query = query.eq("course_unit_id", scope_id)
        elif scope == "student":
            query = query.eq("student_id", scope_id)

        if date_from:
            query = query.gte("timestamp", date_from if "T" in date_from else f"{date_from}T00:00:00")
        if date_to:
            end = date_to if "T" in date_to else f"{date_to}T23:59:59"
            query = query.lte("timestamp", end)

        records = query.execute().data or []
    except Exception as e:
        logger.error("[AI_SUMMARY] Fetch failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch attendance records.")

    if not records:
        raise HTTPException(status_code=404, detail="No attendance records found for the selected filters.")

    truncated = len(records) >= AI_RECORD_LIMIT

    student_ids = list({r["student_id"] for r in records if r.get("student_id")})
    student_map = {}
    if student_ids:
        students_resp = supabase_admin.table("students") \
            .select("id, name") \
            .in_("id", student_ids).execute()
        student_map = {s["id"]: s["name"] for s in (students_resp.data or [])}

    student_stats = defaultdict(
        lambda: {"present": 0, "failed": 0, "spoof": 0, "name": "Unknown"}
    )

    scan_success = scan_failed = scan_spoof = 0
    for r in records:
        sid = r.get("student_id") or "unknown"
        student_stats[sid]["name"] = student_map.get(sid, sid)
        verified = r.get("verified")
        if verified == "success":
            student_stats[sid]["present"] += 1
            scan_success += 1
        elif verified == "spoof":
            student_stats[sid]["spoof"] += 1
            scan_spoof += 1
        else:
            student_stats[sid]["failed"] += 1
            scan_failed += 1

    student_summary_rows = []
    at_risk = []
    eligible_pcts = []

    for sid, data in student_stats.items():
        counted = data["present"] + data["failed"]
        total = counted + data["spoof"]
        pct = round((data["present"] / counted) * 100, 1) if counted > 0 else 0
        row = {
            "student_id": sid,
            "name": data["name"],
            "present": data["present"],
            "failed": data["failed"],
            "spoof": data["spoof"],
            "total": total,
            "attendance_pct": pct,
        }
        student_summary_rows.append(row)
        if counted >= AI_MIN_SESSIONS:
            eligible_pcts.append(pct)
            if pct < AI_AT_RISK_PCT:
                at_risk.append({
                    "name": data["name"],
                    "attendance_pct": pct,
                    "sessions": counted,
                })

    overall_pct = (
        round(sum(eligible_pcts) / len(eligible_pcts), 1)
        if eligible_pcts else 0
    )
    scan_total = scan_success + scan_failed + scan_spoof
    scan_success_rate = (
        round((scan_success / scan_total) * 100, 1) if scan_total > 0 else 0
    )

    stats = {
        "total_students": len(student_summary_rows),
        "total_records": len(records),
        "overall_attendance_pct": overall_pct,
        "scan_success_rate": scan_success_rate,
        "spoof_count": scan_spoof,
        "at_risk_count": len(at_risk),
        "min_sessions_for_at_risk": AI_MIN_SESSIONS,
        "at_risk_threshold_pct": AI_AT_RISK_PCT,
        "students": sorted(student_summary_rows, key=lambda x: x["attendance_pct"]),
    }

    scope_label = {
        "institution": f"all students at {institution_name}",
        "course_unit": f"course unit {course_unit_name or scope_id} at {institution_name}",
        "student": f"student {student_map.get(scope_id, scope_id)} at {institution_name}",
    }[scope]

    date_range_label = ""
    if date_from or date_to:
        date_range_label = f" (from {date_from or 'start'} to {date_to or 'today'})"

    at_risk_lines = "\n".join(
        f"- {s['name']}: {s['attendance_pct']}% ({s['sessions']} sessions)"
        for s in sorted(at_risk, key=lambda x: x["attendance_pct"])
    ) or "- None"

    prompt = f"""You are an academic attendance analyst for {institution_name}.

Write a concise report for {scope_label}{date_range_label}. Stats are pre-computed — do not recalculate.

Sections (use these exact headings):
1. OVERALL SUMMARY — one sentence
2. KEY TRENDS — 3–5 bullets
3. AT-RISK STUDENTS — reference the list below only
4. RECOMMENDATIONS — 3 actionable items

Pre-computed stats:
- Students with records: {stats['total_students']}
- Scans analyzed: {stats['total_records']}{' (capped at limit — mention data may be partial)' if truncated else ''}
- Average student attendance (success / (success+failed), min {AI_MIN_SESSIONS} sessions): {overall_pct}%
- Scan success rate (all scans): {scan_success_rate}%
- Spoof detections: {scan_spoof}
- At-risk (below {AI_AT_RISK_PCT}%): {len(at_risk)}

At-risk list:
{at_risk_lines}

No preamble or closing remarks."""

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": APP_URL,
                    "X-Title": "FaceAttend AI Summary",
                },
                json={
                    "model": AI_SUMMARY_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            result = response.json()
            choices = result.get("choices") or []
            if not choices:
                raise ValueError("OpenRouter returned no choices")
            summary_text = (choices[0].get("message") or {}).get("content", "").strip()
            if not summary_text:
                raise ValueError("OpenRouter returned empty content")
    except httpx.HTTPStatusError as e:
        logger.error(
            "[AI_SUMMARY] OpenRouter HTTP error: %s — %s",
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(status_code=502, detail="AI service returned an error. Try again shortly.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[AI_SUMMARY] OpenRouter call failed: %r", e)
        raise HTTPException(status_code=502, detail="Failed to reach AI service.")

    await log_event(
        AuditAction.AI_SUMMARY_GENERATED,
        actor_id=user.id,
        actor_email=getattr(user, "email", None),
        institution_id=effective_institution_id,
        resource_type="attendance_summary",
        metadata={
            "scope": scope,
            "scope_id": scope_id,
            "records": len(records),
            "truncated": truncated,
            "at_risk_count": len(at_risk),
        },
        request=request,
    )

    return {
        "summary": summary_text,
        "stats": stats,
        "at_risk": at_risk,
        "truncated": truncated,
        "scope": scope,
        "scope_id": scope_id,
        "scope_label": scope_label,
        "course_unit_name": course_unit_name,
        "institution": institution_name,
        "date_from": date_from,
        "date_to": date_to,
    }
