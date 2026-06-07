"""
Admin session routes: list sessions, view session details.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.dep import supabase_admin, check_admin, _bool_flag

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-sessions"])


@router.get("/admin/sessions")
async def get_sessions(
    institution_id: str = None,
    limit: int = 100,
    user=Depends(check_admin),
):
    """
    List all attendance sessions for the authenticated institution.
    Super admin can filter by institution_id or see all sessions.
    """
    try:
        profile_resp = supabase_admin.table("profiles") \
            .select("institution_id, is_super_admin, role") \
            .eq("id", user.id).single().execute()

        is_super_admin = _bool_flag(profile_resp.data.get("is_super_admin") if profile_resp.data else None)
        role = profile_resp.data.get("role", "") if profile_resp.data else ""
        user_institution_id = profile_resp.data.get("institution_id") if profile_resp.data else None
        is_super = is_super_admin or role == "super_admin"

        if not is_super and not user_institution_id:
            raise HTTPException(
                status_code=403,
                detail="Institution admin requires institution_id in profile",
            )

        query = (
            supabase_admin.table("sessions")
            .select("*, course_units(name, code), profiles!sessions_lecturer_id_fkey(full_name, email)")
            .order("created_at", desc=True)
            .limit(limit)
        )

        if is_super:
            if institution_id:
                query = query.eq("institution_id", institution_id)
        else:
            query = query.eq("institution_id", user_institution_id)

        rows = query.execute().data or []

        # Format the response
        sessions = []
        for row in rows:
            cu = row.pop("course_units", None)
            creator = row.pop("profiles", None)
            
            session = {
                "id": row.get("id"),
                "institution_id": row.get("institution_id"),
                "course_unit_id": row.get("course_unit_id"),
                "course_unit_name": cu.get("name") if cu else "N/A",
                "course_unit_code": cu.get("code") if cu else None,
                "name": row.get("name"),
                "started_at": row.get("started_at"),
                "ended_at": row.get("ended_at"),
                "status": row.get("status", "active"),
                "lecturer_id": row.get("lecturer_id"),
                "lecturer_name": creator.get("full_name") if creator else "Unknown",
                "lecturer_email": creator.get("email") if creator else None,
                "lecturer_confirmed": row.get("lecturer_confirmed"),
                "confirmed_at": row.get("confirmed_at"),
                "coordinator_id": row.get("coordinator_id"),
                "department_id": row.get("department_id"),
                "created_at": row.get("created_at"),
            }
            sessions.append(session)

        return {"sessions": sessions, "count": len(sessions)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/sessions/{session_id}")
async def get_session_details(
    session_id: str,
    user=Depends(check_admin),
):
    """
    Get detailed information about a specific session including attendance records.
    """
    try:
        profile_resp = supabase_admin.table("profiles") \
            .select("institution_id, is_super_admin, role") \
            .eq("id", user.id).single().execute()

        is_super_admin = _bool_flag(profile_resp.data.get("is_super_admin") if profile_resp.data else None)
        role = profile_resp.data.get("role", "") if profile_resp.data else ""
        user_institution_id = profile_resp.data.get("institution_id") if profile_resp.data else None
        is_super = is_super_admin or role == "super_admin"

        # Fetch session details
        session_query = (
            supabase_admin.table("sessions")
            .select("*, course_units(name, code), profiles!sessions_lecturer_id_fkey(full_name, email)")
            .eq("id", session_id)
            .single()
        )
        session_resp = session_query.execute()
        if not session_resp.data:
            raise HTTPException(status_code=404, detail="Session not found")

        session = session_resp.data

        # Check authorization
        if not is_super and session.get("institution_id") != user_institution_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this session",
            )

        # Fetch attendance records for this session
        records_query = (
            supabase_admin.table("attendance_records")
            .select("*")
            .eq("session_id", session_id)
            .order("timestamp", desc=False)
        )

        records_resp = records_query.execute()
        records = records_resp.data or []

        # Calculate statistics
        total_records = len(records)
        verified_count = sum(1 for r in records if r.get("verified") == "success")
        failed_count = sum(1 for r in records if r.get("verified") == "failed")
        spoof_count = sum(1 for r in records if r.get("verified") == "spoof")

        # Format response
        # Format response
        cu = session.pop("course_units", None)
        creator = session.pop("profiles", None)

        return {
            "session": {
                "id": session.get("id"),
                "institution_id": session.get("institution_id"),
                "course_unit_id": session.get("course_unit_id"),
                "course_unit_name": cu.get("name") if cu else "N/A",
                "course_unit_code": cu.get("code") if cu else None,
                "name": session.get("name"),
                "started_at": session.get("started_at"),
                "ended_at": session.get("ended_at"),
                "status": session.get("status", "active"),
                "lecturer_id": session.get("lecturer_id"),
                "lecturer_name": creator.get("full_name") if creator else "Unknown",
                "lecturer_email": creator.get("email") if creator else None,
                "lecturer_confirmed": session.get("lecturer_confirmed"),
                "confirmed_at": session.get("confirmed_at"),
                "coordinator_id": session.get("coordinator_id"),
                "department_id": session.get("department_id"),
                "created_at": session.get("created_at"),
            },
            "statistics": {
                "total_records": total_records,
                "verified": verified_count,
                "failed": failed_count,
                "spoof": spoof_count,
                "success_rate": round((verified_count / total_records * 100), 1) if total_records > 0 else 0,
            },
            "records": records,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
