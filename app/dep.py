import os
from fastapi import Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Load environment variables FIRST
load_dotenv()

# 2. Define the constants from the environment
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY         = os.getenv("SUPABASE_KEY", "")          # anon key
SUPABASE_SERVICE_KEY = os.getenv("SERVICE_KEY", "")          # service role


class _MissingSupabaseClient:
    def __init__(self, reason: str):
        self._reason = reason

    def __call__(self, *args, **kwargs):
        raise RuntimeError(self._reason)

    def __getattr__(self, _name):
        if _name.startswith("__"):
            raise AttributeError(_name)
        return self


def _build_supabase_client(url: str, key: str, label: str):
    if not url or not key:
        return _MissingSupabaseClient(
            f"{label} is not configured. Set SUPABASE_URL and SUPABASE_KEY/SERVICE_KEY before using Supabase."
        )
    return create_client(url, key)


# 3. Initialize the clients lazily without crashing imports in local/test environments.
supabase: Client | object = _build_supabase_client(SUPABASE_URL, SUPABASE_KEY, "Supabase client")
supabase_admin: Client | object = _build_supabase_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, "Supabase admin client")

# ── Rate limiter ─────────────────────────────────────────────────────────────
def rate_limit_key(request: Request) -> str:
    return getattr(request.state, "org_id", None) or get_remote_address(request)

limiter = Limiter(key_func=rate_limit_key)

# ── Helpers ──────────────────────────────────────────────────────────────────
def _bool_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def normalize_role(role) -> str:
    return str(role or "").strip().lower()


def build_admin_context(profile: dict | None) -> dict:
    profile = profile or {}
    role = normalize_role(profile.get("role"))
    is_admin = _bool_flag(profile.get("is_admin"))
    is_super_admin = _bool_flag(profile.get("is_super_admin"))
    is_super = is_super_admin or role == "super_admin"
    if is_super:
        role = "super_admin"
    is_central_admin = role == "central_admin"
    is_dept_admin = role in {"dept_admin", "admin"}

    return {
        "role": role,
        "is_admin": is_admin or is_super or is_central_admin or is_dept_admin,
        "is_super_admin": is_super_admin,
        "is_super": is_super,
        "is_central_admin": is_central_admin,
        "is_dept_admin": is_dept_admin,
        "can_access_dashboard": is_admin or is_super or is_central_admin or is_dept_admin,
    }


def can_access_feature(profile: dict | None, feature: str, institution_plan: str | None = None) -> bool:
    ctx = build_admin_context(profile)
    feature_name = (feature or "").lower()

    if feature_name in {"analytics", "security", "institutions", "api_keys"}:
        if feature_name == "api_keys":
            return ctx["is_super"] or (ctx["is_dept_admin"] and normalize_role(institution_plan) == "enterprise")
        return ctx["is_super"]

    if feature_name in {"departments", "dept_admins", "deptadmins"}:
        return ctx["is_super"] or ctx["is_central_admin"]

    if feature_name == "billing":
        return ctx["is_super"] or ctx["is_central_admin"] or ctx["is_dept_admin"]

    if feature_name in {"students", "lecturers", "course_units", "sessions", "team"}:
        if ctx["is_super"]:
            return False
        return ctx["is_dept_admin"] or ctx["is_central_admin"]

    if feature_name == "audit":
        return ctx["is_super"] or ctx["is_dept_admin"] or ctx["is_central_admin"]

    if feature_name in {"attendance", "ai_summary"}:
        return ctx["can_access_dashboard"] and not ctx["is_super"]

    return ctx["can_access_dashboard"]

# ── Auth dependencies ────────────────────────────────────────────────────────

async def verify_supabase_token(authorization: str = Header(None)):
    """Verify that the request comes from a valid authenticated Supabase user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token verification failed")


async def check_admin(authorization: str = Header(None)):
    """Verify that the user is authenticated, is an admin, and their institution is active."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user_id = user_response.user.id
        resp = supabase_admin.table("profiles") \
            .select("is_admin, is_super_admin, role, institution_id") \
            .eq("id", user_id).limit(1).execute()

        profile_data = resp.data[0] if resp.data else None
        if not profile_data:
            raise HTTPException(status_code=403, detail="Admin profile not found or incomplete")

        profile_context = build_admin_context(profile_data)
        if not profile_context["can_access_dashboard"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        institution_id = profile_data.get("institution_id")
        if institution_id and not profile_context["is_super"]:
            inst_resp = supabase_admin.table("institutions").select("status") \
                .eq("id", institution_id).limit(1).execute()
            if inst_resp.data:
                status = inst_resp.data[0].get("status", "active")
                if status == "pending":
                    raise HTTPException(
                        status_code=403,
                        detail="Your institution is pending approval. You will be notified once approved."
                    )
                elif status == "suspended":
                    raise HTTPException(
                        status_code=403,
                        detail="Your institution account has been suspended. Contact support."
                    )

        return user_response.user
    except HTTPException:
        raise
    except Exception as e:
        print(f"[check_admin] error: {e!r}")
        raise HTTPException(status_code=401, detail="Token verification failed")


async def check_super_admin(authorization: str = Header(None)):
    """Verify that the user is a super admin."""
    user = await check_admin(authorization)
    user_id = user.id
    resp = supabase_admin.table("profiles") \
        .select("is_super_admin, role") \
        .eq("id", user_id).limit(1).execute()
    profile_data   = resp.data[0] if resp.data else None
    profile_context = build_admin_context(profile_data)

    if not profile_context["is_super"]:
        raise HTTPException(status_code=403, detail="Super admin access required")

    return user

def require_enterprise(org_id: str):
    """Raise 403 if the institution is not on the enterprise plan."""
    resp = supabase_admin.table("institutions") \
        .select("plans") \
        .eq("id", org_id) \
        .limit(1).execute()

    inst = resp.data[0] if resp.data else None
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    if inst.get("plans") != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access requires an Enterprise plan. To upgrade, contact abubaker@faceattend.app.",
        )