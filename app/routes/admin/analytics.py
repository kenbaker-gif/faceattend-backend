"""Analytics API endpoints — super admin only."""
from fastapi import APIRouter, Depends, HTTPException
from app.dep import supabase_admin, check_admin, _bool_flag
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


def _require_super_admin(user=Depends(check_admin)):
    profile = supabase_admin.table("profiles") \
        .select("is_super_admin, role") \
        .eq("id", user.id).single().execute()
    p = profile.data or {}
    if not (_bool_flag(p.get("is_super_admin")) or p.get("role") == "super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


@router.get("/revenue")
async def get_revenue_metrics(user=Depends(_require_super_admin)):
    return AnalyticsService.calculate_mrr(supabase_admin)


@router.get("/churn")
async def get_churn_rate(days: int = 30, user=Depends(_require_super_admin)):
    return AnalyticsService.calculate_churn(supabase_admin, days)


@router.get("/usage")
async def get_usage_trends(user=Depends(_require_super_admin)):
    return AnalyticsService.get_usage_trends(supabase_admin)


@router.get("/payments")
async def get_payment_metrics(days: int = 30, user=Depends(_require_super_admin)):
    return AnalyticsService.get_payment_metrics(supabase_admin, days)