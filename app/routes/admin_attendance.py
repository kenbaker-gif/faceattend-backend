"""
Admin attendance routes: records, summary, AI report.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dep import supabase_admin, check_admin, _bool_flag

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-attendance"])

APP_URL = os.getenv("APP_URL", "https://faceattend.app")


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


@router.get("/admin/attendance_summary")
async def get_summary(
    institution_id: str = None,
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
            .select("student_id, verified")

        if is_super:
            if institution_id:
                query = query.eq("institution_id", institution_id)
        else:
            query = query.eq("institution_id", user_institution_id)

        rows = query.execute().data or []
        total_present = sum(1 for r in rows if r.get("verified") == "success")
        total_absent  = sum(1 for r in rows if r.get("verified") == "failed")
        by_student    = {}
        for r in rows:
            sid = r.get("student_id") or "Unknown"
            if r.get("verified") == "success":
                by_student[sid] = by_student.get(sid, 0) + 1
        return {
            "total_present": total_present,
            "total_absent":  total_absent,
            "by_student":    by_student,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/ai-attendance-summary")
async def ai_attendance_summary(
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

    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()

    profile = profile_resp.data or {}
    is_super = _bool_flag(profile.get("is_super_admin")) or profile.get("role", "") == "super_admin"
    user_institution_id = profile.get("institution_id")

    if not is_super and not user_institution_id:
        raise HTTPException(status_code=403, detail="Admin not linked to an institution.")

    effective_institution_id = user_institution_id if not is_super else (institution_id or user_institution_id)

    institution_name = "all institutions"
    if effective_institution_id:
        inst_resp = supabase_admin.table("institutions") \
            .select("name") \
            .eq("id", effective_institution_id).limit(1).execute()
        institution_name = inst_resp.data[0]["name"] if inst_resp.data else effective_institution_id

    try:
        query = supabase_admin.table("attendance_records") \
            .select("student_id, verified, timestamp, course_unit_id")
        if effective_institution_id:
            query = query.eq("institution_id", effective_institution_id)
        query = query.order("timestamp", desc=True) \
            .limit(1000)

        if scope == "course_unit" and scope_id:
            query = query.eq("course_unit_id", scope_id)
        elif scope == "student" and scope_id:
            query = query.eq("student_id", scope_id)

        if date_from:
            query = query.gte("timestamp", date_from)
        if date_to:
            query = query.lte("timestamp", date_to + "T23:59:59")

        records = query.execute().data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch attendance records: {str(e)}")

    if not records:
        raise HTTPException(status_code=404, detail="No attendance records found for the selected filters.")

    student_ids = list({r["student_id"] for r in records if r.get("student_id")})
    students_resp = supabase_admin.table("students") \
        .select("id, name") \
        .in_("id", student_ids).execute()
    student_map = {s["id"]: s["name"] for s in (students_resp.data or [])}

    student_stats = defaultdict(lambda: {"present": 0, "absent": 0, "name": "Unknown"})

    for r in records:
        sid = r.get("student_id") or "unknown"
        student_stats[sid]["name"] = student_map.get(sid, sid)
        if r.get("verified") == "success":
            student_stats[sid]["present"] += 1
        else:
            student_stats[sid]["absent"] += 1

    student_summary_rows = []
    at_risk = []

    for sid, data in student_stats.items():
        total = data["present"] + data["absent"]
        pct = round((data["present"] / total) * 100, 1) if total > 0 else 0
        row = {
            "student_id": sid,
            "name": data["name"],
            "present": data["present"],
            "absent": data["absent"],
            "total": total,
            "attendance_pct": pct,
        }
        student_summary_rows.append(row)
        if pct < 75:
            at_risk.append({"name": data["name"], "attendance_pct": pct})

    overall_present = sum(r["present"] for r in student_summary_rows)
    overall_total   = sum(r["total"]   for r in student_summary_rows)
    overall_pct     = round((overall_present / overall_total) * 100, 1) if overall_total > 0 else 0

    stats = {
        "total_students":  len(student_summary_rows),
        "total_records":   len(records),
        "overall_attendance_pct": overall_pct,
        "at_risk_count":   len(at_risk),
        "students":        sorted(student_summary_rows, key=lambda x: x["attendance_pct"]),
    }

    scope_label = {
        "institution": f"all students at {institution_name}",
        "course_unit": f"course unit {scope_id} at {institution_name}",
        "student":     f"student {student_map.get(scope_id, scope_id)} at {institution_name}",
    }.get(scope, institution_name)

    date_range_label = ""
    if date_from or date_to:
        date_range_label = f" (from {date_from or 'start'} to {date_to or 'today'})"

    student_lines = "\n".join(
        f"- {r['name']}: {r['attendance_pct']}% ({r['present']}/{r['total']} sessions)"
        for r in sorted(student_summary_rows, key=lambda x: x["attendance_pct"])
    )

    prompt = f"""You are an academic attendance analyst preparing a report for {institution_name}.

Analyze the following attendance data for {scope_label}{date_range_label} and produce a structured report with these exact sections:

1. OVERALL SUMMARY — one sentence conclusion
2. KEY TRENDS — 3 to 5 bullet points about patterns you observe
3. AT-RISK STUDENTS — list students below 75% attendance and briefly explain the concern
4. RECOMMENDATIONS — 3 actionable recommendations for the institution or lecturer

Data:
\"\"\"
Total students: {stats['total_students']}
Overall attendance rate: {overall_pct}%
At-risk students (below 75%): {len(at_risk)}

Per-student breakdown:
{student_lines}
\"\"\"

Be concise, professional, and specific. Do not add preamble or closing remarks."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": APP_URL,
                    "X-Title": "FaceAttend AI Summary",
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            result = response.json()
            summary_text = result["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        logger.error(f"[AI_SUMMARY] OpenRouter HTTP error: {e.response.status_code} — {e.response.text}")
        raise HTTPException(status_code=502, detail="AI service returned an error. Try again shortly.")
    except Exception as e:
        logger.error(f"[AI_SUMMARY] OpenRouter call failed: {repr(e)}")
        raise HTTPException(status_code=502, detail="Failed to reach AI service.")

    return {
        "summary": summary_text,
        "stats": stats,
        "at_risk": at_risk,
        "scope": scope,
        "scope_id": scope_id,
        "institution": institution_name,
        "date_from": date_from,
        "date_to": date_to,
    }
