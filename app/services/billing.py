"""Billing service for plan management, proration, and invoicing."""
from datetime import datetime, timedelta
from typing import Optional, Dict
from app.models.billing import ProrationCalculation, Invoice


class BillingService:
    """Core billing logic for subscription management."""
    
    PLAN_PRICES = {
        "free": 0,
        "premium": 99,    # USD per month (matches Pesapal growth plan)
        "enterprise": 199  # USD per month (matches Pesapal pro plan)
    }
    
    PLAN_CURRENCY = "USD"
    
    STUDENT_LIMITS = {
        "free": 50,
        "premium": 500,
        "enterprise": float('inf')
    }
    
    @classmethod
    def calculate_proration(
        cls,
        current_plan: str,
        new_plan: str,
        subscription_end: datetime
    ) -> ProrationCalculation:
        """Calculate prorated amount for plan change."""
        now = datetime.utcnow()
        # Use date difference to avoid truncation issues and match expectations
        days_remaining = max(0, (subscription_end.date() - now.date()).days)
        
        current_price = cls.PLAN_PRICES[current_plan]
        new_price = cls.PLAN_PRICES[new_plan]
        
        # Daily rates (assume 30-day month)
        current_daily = current_price / 30
        new_daily = new_price / 30
        
        # Calculate refund/charge
        refund = current_daily * days_remaining
        charge = new_daily * days_remaining
        net = charge - refund
        
        return ProrationCalculation(
            current_plan=current_plan,
            new_plan=new_plan,
            days_remaining=days_remaining,
            current_plan_daily_rate=round(current_daily, 2),
            new_plan_daily_rate=round(new_daily, 2),
            refund_amount=round(refund, 2),
            charge_amount=round(charge, 2),
            net_amount=round(net, 2)
        )
    
    @classmethod
    def validate_plan_change(
        cls,
        current_plan: str,
        new_plan: str,
        current_student_count: int
    ) -> tuple[bool, Optional[str]]:
        """Validate if plan change is allowed."""
        # Can't downgrade if exceeds new limit
        new_limit = cls.STUDENT_LIMITS[new_plan]
        if current_student_count > new_limit:
            return False, f"Cannot downgrade: you have {current_student_count} students but {new_plan} plan allows {new_limit}"
        
        # Free plan cannot be "upgraded" to - only subscribed to
        if new_plan == "free" and current_plan != "free":
            # Allow downgrading to free plan without an error message
            return True, None
        
        return True, None
    
    @classmethod
    def generate_invoice(
        cls,
        institution_id: str,
        plan: str,
        description: str,
        due_days: int = 7
    ) -> Invoice:
        """Generate invoice for subscription."""
        now = datetime.utcnow()
        return Invoice(
            invoice_id=f"INV-{institution_id[:8]}-{int(now.timestamp())}",
            institution_id=institution_id,
            plan=plan,
            amount=cls.PLAN_PRICES[plan],
            currency=cls.PLAN_CURRENCY,
            issue_date=now,
            due_date=now + timedelta(days=due_days),
            status="pending",
            description=description
        )
    
    @classmethod
    def is_in_grace_period(
        cls,
        subscription_end: datetime,
        grace_days: int = 3
    ) -> bool:
        """Check if subscription is in grace period."""
        now = datetime.utcnow()
        grace_end = subscription_end + timedelta(days=grace_days)
        return subscription_end < now <= grace_end
    
    @classmethod
    def calculate_next_renewal(
        cls,
        current_end: datetime,
        plan_duration_days: int = 30
    ) -> datetime:
        """Calculate next renewal date."""
        return current_end + timedelta(days=plan_duration_days)
