import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "anon-key")
os.environ.setdefault("SERVICE_KEY", "service-key")

from app.dep import build_admin_context, can_access_feature


def test_super_admin_permissions():
    profile = {"is_super_admin": True, "role": "admin", "institution_id": "inst-1"}
    ctx = build_admin_context(profile)

    assert ctx["is_super_admin"] is True
    assert ctx["is_super"] is True
    assert can_access_feature(profile, "analytics") is True
    assert can_access_feature(profile, "security") is True
    assert can_access_feature(profile, "api_keys") is True


def test_central_admin_permissions():
    profile = {"is_super_admin": False, "role": "central_admin", "institution_id": "inst-1"}
    ctx = build_admin_context(profile)

    assert ctx["is_central_admin"] is True
    assert ctx["is_super"] is False
    assert can_access_feature(profile, "analytics") is False
    assert can_access_feature(profile, "departments") is True
    assert can_access_feature(profile, "billing") is True


def test_dept_admin_permissions():
    profile = {"is_super_admin": False, "role": "dept_admin", "institution_id": "inst-1"}
    ctx = build_admin_context(profile)

    assert ctx["is_dept_admin"] is True
    assert ctx["is_super"] is False
    assert can_access_feature(profile, "students") is True
    assert can_access_feature(profile, "billing") is True
    assert can_access_feature(profile, "analytics") is False
    assert can_access_feature(profile, "api_keys") is False
