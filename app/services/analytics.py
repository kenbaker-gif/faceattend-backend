"""Analytics service for billing and usage metrics."""
from datetime import datetime, timedelta
from typing import Dict, List
from supabase import Client


class AnalyticsService:
    """Calculate business metrics and analytics."""
    
    PLAN_PRICES = {"free": 0, "premium": 3000, "enterprise": 10000}
    
    @staticmethod
    def calculate_mrr(supabase: Client) -> Dict:
        """Calculate Monthly Recurring Revenue."""
        institutions = supabase.table("institutions").select("plan").execute()
        
        mrr = sum(AnalyticsService.PLAN_PRICES.get(inst.get("plan", "free"), 0) 
                  for inst in institutions.data)
        arr = mrr * 12
        
        plan_breakdown = {}
        for plan, price in AnalyticsService.PLAN_PRICES.items():
            count = sum(1 for inst in institutions.data if inst.get("plan") == plan)
            plan_breakdown[plan] = {"count": count, "mrr": count * price}
        
        return {
            "mrr": mrr,
            "arr": arr,
            "total_institutions": len(institutions.data),
            "plan_breakdown": plan_breakdown
        }
    
    @staticmethod
    def calculate_churn(supabase: Client, days: int = 30) -> Dict:
        """Calculate churn rate for given period."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Downgrades/cancellations from plan_change_history
        changes = supabase.table("plan_change_history").select("*").gte("created_at", cutoff).execute()
        
        downgrades = sum(1 for c in changes.data if c.get("from_plan") in ["premium", "enterprise"] 
                        and c.get("to_plan") in ["free", "premium"])
        
        institutions = supabase.table("institutions").select("id", count="exact").execute()
        total = institutions.count or 1
        
        churn_rate = (downgrades / total) * 100
        
        return {
            "churn_rate": round(churn_rate, 2),
            "churned_count": downgrades,
            "period_days": days,
            "total_institutions": total
        }
    
    @staticmethod
    def get_usage_trends(supabase: Client) -> List[Dict]:
        """Get student usage by institution plan."""
        institutions = supabase.table("institutions").select("id, name, plan").execute()
        
        trends = []
        for inst in institutions.data:
            students = supabase.table("students").select("id", count="exact").eq("institution_id", inst["id"]).execute()
            count = students.count or 0
            
            plan = inst.get("plan", "free")
            limits = {"free": 50, "premium": 500, "enterprise": 999999}
            
            trends.append({
                "institution": inst.get("name", "Unknown"),
                "plan": plan,
                "students": count,
                "limit": limits[plan],
                "utilization": round((count / limits[plan]) * 100, 1) if limits[plan] > 0 else 0
            })
        
        return sorted(trends, key=lambda x: x["utilization"], reverse=True)
    
    @staticmethod
    def get_payment_metrics(supabase: Client, days: int = 30) -> Dict:
        """Calculate payment success rate."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        payments = supabase.table("payments").select("status").gte("payment_date", cutoff).execute()
        
        if not payments.data:
            return {"success_rate": 0, "total_payments": 0, "successful": 0, "failed": 0}
        
        successful = sum(1 for p in payments.data if p.get("status") == "success")
        total = len(payments.data)
        
        return {
            "success_rate": round((successful / total) * 100, 2) if total > 0 else 0,
            "total_payments": total,
            "successful": successful,
            "failed": total - successful,
            "period_days": days
        }
