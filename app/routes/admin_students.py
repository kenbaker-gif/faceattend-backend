"""
Admin student routes: upload face photos, list, delete.
Same paths and Supabase tables as before — refactor only.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)

from app.dep import supabase_admin, verify_supabase_token, check_admin, _bool_flag
from app.utils.mvp_sync import MVP_URL, trigger_sync_in_background

router = APIRouter(tags=["admin-students"])

BUCKET = "raw_faces"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload-student-face")
async def upload_student(
    background_tasks: BackgroundTasks,
    student_id: str = Form(...),
    name: str = Form(...),
    institution_id: str = Form(default="NKU"),
    file: UploadFile = File(...),
    authorization: str = Header(None),
    user=Depends(verify_supabase_token),
):
    if not student_id.strip():
        raise HTTPException(status_code=400, detail="student_id cannot be empty.")
    if not name.strip():
        raise HTTPException(status_code=400, detail="name cannot be empty.")
    if not institution_id.strip():
        raise HTTPException(status_code=400, detail="institution_id cannot be empty.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{file.content_type}'.")

    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    profile_resp = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute()
    profile = profile_resp.data or {}
    is_super = _bool_flag(profile.get("is_super_admin")) or profile.get("role", "") == "super_admin"
    user_institution_id = profile.get("institution_id")

    if not is_super:
        if not user_institution_id:
            raise HTTPException(status_code=403, detail="Institution admin requires institution_id in profile")
        effective_institution_id = user_institution_id
    else:
        effective_institution_id = institution_id.strip()

    file_path = f"{effective_institution_id}/{student_id.strip()}/{file.filename}"

    try:
        try:
            supabase_admin.storage.from_(BUCKET).remove([file_path])
        except Exception:
            pass

        supabase_admin.storage.from_(BUCKET).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type},
        )

        image_url = supabase_admin.storage.from_(BUCKET).get_public_url(file_path)

        supabase_admin.table("students").upsert({
            "id": student_id.strip(),
            "name": name.strip(),
            "institution_id": effective_institution_id,
        }).execute()

        sync_triggered = False
        if file.filename == "4.jpg":
            token = authorization.replace("Bearer ", "").strip() if authorization else None

            if token and MVP_URL:
                print(f"📸 4th photo uploaded for {student_id} — triggering auto-sync...")
                background_tasks.add_task(trigger_sync_in_background, token)
                sync_triggered = True
            else:
                if not token:
                    print(f"⚠️  Skipping auto-sync for {student_id}: no auth token available.")
                if not MVP_URL:
                    print(f"⚠️  Skipping auto-sync for {student_id}: MVP_URL not configured.")

        return {
            "success": True,
            "student_id": student_id.strip(),
            "name": name.strip(),
            "institution_id": effective_institution_id,
            "image_url": image_url,
            "file_path": file_path,
            "sync_triggered": sync_triggered,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/students")
async def list_students(
    institution_id: str = None,
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

        if not is_super and not user_institution_id:
            raise HTTPException(status_code=403, detail="Institution admin requires institution_id in profile")

        query = supabase_admin.table("students").select("*").order("name")

        if is_super:
            if institution_id:
                query = query.eq("institution_id", institution_id)
        else:
            query = query.eq("institution_id", user_institution_id)

        response = query.execute()
        students = response.data or []
        return {"students": students, "count": len(students)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/students/{student_id}")
async def delete_student(
    student_id: str,
    user=Depends(check_admin),
):
    try:
        profile_resp = supabase_admin.table("profiles") \
            .select("institution_id, is_super_admin, role") \
            .eq("id", user.id).single().execute()
        profile = profile_resp.data or {}
        is_super = _bool_flag(profile.get("is_super_admin")) or profile.get("role", "") == "super_admin"
        user_institution_id = profile.get("institution_id")

        if not is_super and not user_institution_id:
            raise HTTPException(status_code=403, detail="Institution admin requires institution_id in profile")

        resp = supabase_admin.table("students").select("institution_id") \
            .eq("id", student_id).limit(1).execute()
        institution_id = resp.data[0].get("institution_id") if resp.data else None

        if institution_id and not is_super and institution_id != user_institution_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this student")

        if institution_id:
            folder = f"{institution_id}/{student_id}"
            files = supabase_admin.storage.from_(BUCKET).list(folder)
            if files:
                paths = [f"{folder}/{f['name']}" for f in files]
                supabase_admin.storage.from_(BUCKET).remove(paths)

        attendance_delete = supabase_admin.table("attendance_records").delete().eq("student_id", student_id)
        student_delete = supabase_admin.table("students").delete().eq("id", student_id)
        if institution_id:
            attendance_delete = attendance_delete.eq("institution_id", institution_id)
            student_delete = student_delete.eq("institution_id", institution_id)
        attendance_delete.execute()
        student_delete.execute()

        return {"success": True, "deleted_student_id": student_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
