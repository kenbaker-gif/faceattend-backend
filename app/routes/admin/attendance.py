"""
Admin attendance routes: records, summary, AI report.
"""

from __future__ import annotations

import logging
import os
import re
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
AI_TOP_PERFORMER_PCT = float(os.getenv("AI_TOP_PERFORMER_PCT", "90"))
AI_MIN_SESSIONS = int(os.getenv("AI_MIN_SESSIONS", "3"))
AI_SUMMARY_MODEL = os.getenv("AI_SUMMARY_MODEL", "deepseek/deepseek-chat")
VALID_SCOPES = frozenset({"institution", "course_unit", "student"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _initials(name: str) -> str:
    """Return up to 2 initials from a name."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "??"


def _strip_markdown(text: str) -> str:
    """
    Remove common markdown formatting characters from AI output so the
    report arrives as clean plain text regardless of what the model emits.
    """
    # Remove bold / italic / bold-italic  (**text**, *text*, ***text***)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text, flags=re.DOTALL)
    # Remove __underline__ / _italic_
    text = re.sub(r"_{1,2}(.*?)_{1,2}", r"\1", text, flags=re.DOTALL)
    # Remove ATX headings  (## Heading → Heading)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove inline code and fenced code blocks
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text, flags=re.DOTALL)
    # Collapse more than two consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
        role = profile_resp.data.get("role", "") if profile_resp.data else ""
        user_institution_id = profile_resp.data.get("institution_id") if profile_resp.data else None
        is_super = is_super_admin or role == "super_admin"

        if is_super:
            raise HTTPException(
                status_code=403,
                detail="Super admins use /admin/super/security-summary for aggregate security data.",
            )

        if not user_institution_id:
            raise HTTPException(
                status_code=403,
                detail="Institution admin requires institution_id in profile",
            )

        query = (
            supabase_admin.table("attendance_records")
            .select("*, course_units(name)")
            .order("timestamp", desc=True)
            .limit(limit)
            .eq("institution_id", user_institution_id)
        )

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

    # ── Scope validation ────────────────────────────────────────────────────
    scope = (scope or "institution").strip().lower()
    if scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope. Use one of: {', '.join(sorted(VALID_SCOPES))}.",
        )
    if scope in ("course_unit", "student") and not scope_id:
        raise HTTPException(
            status_code=400,
            detail=f"scope_id is required when scope is '{scope}'.",
        )

    # ── Admin profile ───────────────────────────────────────────────────────
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

    # ── Institution & course unit names ─────────────────────────────────────
    institution_name = effective_institution_id
    inst_resp = supabase_admin.table("institutions") \
        .select("name").eq("id", effective_institution_id).limit(1).execute()
    if inst_resp.data:
        institution_name = inst_resp.data[0]["name"]

    course_unit_name = None
    if scope == "course_unit" and scope_id:
        cu_resp = supabase_admin.table("course_units") \
            .select("name").eq("id", scope_id).limit(1).execute()
        course_unit_name = cu_resp.data[0]["name"] if cu_resp.data else scope_id

    # ── Fetch attendance records ─────────────────────────────────────────────
    try:
        query = (
            supabase_admin.table("attendance_records")
            .select("student_id, verified, timestamp, course_unit_id")
            .eq("institution_id", effective_institution_id)
            .order("timestamp", desc=True)
            .limit(AI_RECORD_LIMIT)
        )

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
        raise HTTPException(
            status_code=404,
            detail="No attendance records found for the selected filters.",
        )

    truncated = len(records) >= AI_RECORD_LIMIT

    # ── Resolve student names ────────────────────────────────────────────────
    student_ids = list({r["student_id"] for r in records if r.get("student_id")})
    student_map: dict[str, str] = {}
    if student_ids:
        students_resp = supabase_admin.table("students") \
            .select("id, name").in_("id", student_ids).execute()
        student_map = {s["id"]: s["name"] for s in (students_resp.data or [])}

    # ── Per-student stats ────────────────────────────────────────────────────
    student_stats: dict = defaultdict(
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
    top_performers = []
    eligible_pcts = []

    for sid, data in student_stats.items():
        counted = data["present"] + data["failed"]
        total = counted + data["spoof"]
        pct = round((data["present"] / counted) * 100, 1) if counted > 0 else 0
        row = {
            "student_id": sid,
            "name": data["name"],
            "initials": _initials(data["name"]),
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
            if pct >= AI_TOP_PERFORMER_PCT:
                top_performers.append({
                    "name": data["name"],
                    "attendance_pct": pct,
                    "sessions": counted,
                })

    overall_pct = round(sum(eligible_pcts) / len(eligible_pcts), 1) if eligible_pcts else 0
    scan_total = scan_success + scan_failed + scan_spoof
    scan_success_rate = round((scan_success / scan_total) * 100, 1) if scan_total > 0 else 0

    # Sort lists
    at_risk = sorted(at_risk, key=lambda x: x["attendance_pct"])
    top_performers = sorted(top_performers, key=lambda x: x["attendance_pct"], reverse=True)[:5]

    # ── Course unit breakdown (institution scope only) ───────────────────────
    cu_breakdown = []
    if scope == "institution":
        cu_ids = list({r["course_unit_id"] for r in records if r.get("course_unit_id")})
        cu_map: dict[str, str] = {}
        if cu_ids:
            cu_resp = supabase_admin.table("course_units") \
                .select("id, name").in_("id", cu_ids).execute()
            cu_map = {c["id"]: c["name"] for c in (cu_resp.data or [])}

        cu_agg: dict = defaultdict(lambda: {"present": 0, "total": 0, "name": "Unknown"})
        for r in records:
            cuid = r.get("course_unit_id") or "unknown"
            cu_agg[cuid]["name"] = cu_map.get(cuid, cuid)
            cu_agg[cuid]["total"] += 1
            if r.get("verified") == "success":
                cu_agg[cuid]["present"] += 1

        cu_breakdown = sorted(
            [
                {
                    "name": v["name"],
                    "attendance_pct": round((v["present"] / v["total"]) * 100, 1) if v["total"] else 0,
                    "total_scans": v["total"],
                }
                for v in cu_agg.values()
            ],
            key=lambda x: x["attendance_pct"],
        )

    # ── Stats object ─────────────────────────────────────────────────────────
    stats = {
        "total_students": len(student_summary_rows),
        "total_records": len(records),
        "overall_attendance_pct": overall_pct,
        "scan_success_rate": scan_success_rate,
        "spoof_count": scan_spoof,
        "at_risk_count": len(at_risk),
        "top_performer_count": len(top_performers),
        "min_sessions_for_at_risk": AI_MIN_SESSIONS,
        "at_risk_threshold_pct": AI_AT_RISK_PCT,
        "top_performer_threshold_pct": AI_TOP_PERFORMER_PCT,
        "students": sorted(student_summary_rows, key=lambda x: x["attendance_pct"]),
    }

    # ── Build prompt ─────────────────────────────────────────────────────────
    scope_label = {
        "institution": f"all students at {institution_name}",
        "course_unit": f"course unit '{course_unit_name or scope_id}' at {institution_name}",
        "student": f"student {student_map.get(scope_id, scope_id)} at {institution_name}",
    }[scope]

    date_range_label = ""
    if date_from or date_to:
        date_range_label = f" (from {date_from or 'start'} to {date_to or 'today'})"

    at_risk_lines = "\n".join(
        f"- {s['name']}: {s['attendance_pct']}% ({s['sessions']} sessions)"
        for s in at_risk
    ) or "- None"

    top_lines = "\n".join(
        f"- {s['name']}: {s['attendance_pct']}% ({s['sessions']} sessions)"
        for s in top_performers
    ) or "- None"

    cu_section = ""
    if cu_breakdown:
        cu_lines = "\n".join(
            f"- {c['name']}: {c['attendance_pct']}% ({c['total_scans']} scans)"
            for c in cu_breakdown
        )
        cu_section = f"\nCourse unit breakdown (worst to best):\n{cu_lines}\n"

    # System message: role + hard formatting rules
    system_message = (
        "You are an academic attendance analyst writing formal institutional reports. "
        "Write entirely in plain prose. "
        "Do not use asterisks, pound signs, underscores, backticks, or any other markdown syntax. "
        "Do not bold or italicise any text. "
        "Use only the exact section headings provided, written in ALL CAPS on their own line. "
        "All statistics are pre-computed — do not recalculate or invent figures. "
        "Keep the report concise and professional."
    )

    prompt = f"""Write a concise attendance report for {scope_label}{date_range_label}.

Use these section headings exactly, each on its own line in ALL CAPS:

OVERALL SUMMARY
One sentence on overall attendance health.

KEY TRENDS
3 to 5 bullet points starting with a dash (-). Plain sentences only, no sub-bullets.

COURSE UNIT BREAKDOWN
{"Brief note on which course units have the lowest and highest attendance. Reference the breakdown list below." if cu_breakdown else "Skip — not applicable for this scope."}

TOP PERFORMERS
Reference the top performers list below. Skip this section if the list is empty.

AT-RISK STUDENTS
Reference the at-risk list below only. Do not recalculate percentages.

RECOMMENDATIONS
3 specific, actionable items addressed to academic coordinators.

Pre-computed stats:
- Students with records: {stats['total_students']}
- Scans analysed: {stats['total_records']}{' (capped at limit — data may be partial)' if truncated else ''}
- Average student attendance (success / counted, min {AI_MIN_SESSIONS} sessions): {overall_pct}%
- Scan success rate (all scans): {scan_success_rate}%
- Spoof detections: {scan_spoof}
- At-risk (below {AI_AT_RISK_PCT}%): {len(at_risk)}
- Top performers ({AI_TOP_PERFORMER_PCT}%+): {len(top_performers)}
{cu_section}
Top performers:
{top_lines}

At-risk students:
{at_risk_lines}

Strict output rules:
- Plain text only. No asterisks, no markdown, no bold, no italics, no # headings.
- No preamble before OVERALL SUMMARY.
- No closing remarks after RECOMMENDATIONS.
- Do not invent any data not present in the stats above."""

    # ── Call OpenRouter ──────────────────────────────────────────────────────
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
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt},
                    ],
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
        raise HTTPException(
            status_code=502,
            detail="AI service returned an error. Try again shortly.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[AI_SUMMARY] OpenRouter call failed: %r", e)
        raise HTTPException(status_code=502, detail="Failed to reach AI service.")

    # ── Strip any stray markdown the model emitted anyway ───────────────────
    summary_text = _strip_markdown(summary_text)

    # ── Audit log ────────────────────────────────────────────────────────────
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
            "top_performer_count": len(top_performers),
        },
        request=request,
    )

    return {
        "summary": summary_text,
        "stats": stats,
        "at_risk": at_risk,
        "top_performers": top_performers,
        "course_unit_breakdown": cu_breakdown,
        "truncated": truncated,
        "scope": scope,
        "scope_id": scope_id,
        "scope_label": scope_label,
        "course_unit_name": course_unit_name,
        "institution": institution_name,
        "date_from": date_from,
        "date_to": date_to,
    }