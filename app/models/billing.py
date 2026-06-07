"""Pydantic models for billing and subscription management."""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class PlanUpgradeRequest(BaseModel):
    """Request to upgrade/downgrade subscription plan."""
    institution_id: str = Field(..., description="Institution UUID")
    new_plan: Literal["free", "premium", "enterprise"] = Field(..., description="Target plan")
    payment_method: Optional[str] = Field(None, description="Payment method for upgrades")


class PlanUpgradeResponse(BaseModel):
    """Response from plan change operation."""
    success: bool
    message: str
    new_plan: str
    effective_date: datetime
    prorated_amount: Optional[float] = None
    payment_required: bool = False
    payment_link: Optional[str] = None


class ProrationCalculation(BaseModel):
    """Proration calculation for plan changes."""
    current_plan: str
    new_plan: str
    days_remaining: int
    current_plan_daily_rate: float
    new_plan_daily_rate: float
    refund_amount: float = 0.0
    charge_amount: float = 0.0
    net_amount: float = Field(..., description="Positive = charge, negative = credit")


class Invoice(BaseModel):
    """Invoice details for subscription payment."""
    invoice_id: str
    institution_id: str
    plan: str
    amount: float
    currency: str = "KES"
    issue_date: datetime
    due_date: datetime
    status: Literal["pending", "paid", "overdue", "cancelled"]
    description: str


class InvoiceCreate(BaseModel):
    """Create new invoice."""
    institution_id: str
    plan: str
    amount: float
    description: str
    due_days: int = Field(default=7, description="Days until invoice due")


class PaymentHistory(BaseModel):
    """Payment history record."""
    payment_id: str
    institution_id: str
    amount: float
    currency: str
    plan: str
    payment_date: datetime
    payment_method: str
    transaction_id: str
    status: Literal["success", "pending", "failed", "refunded"]


class GracePeriodConfig(BaseModel):
    """Grace period configuration for expired subscriptions."""
    enabled: bool = True
    days: int = Field(default=3, description="Grace period in days after expiry")
    features_limited: bool = Field(default=True, description="Limit features during grace period")


class AutoRenewalConfig(BaseModel):
    """Auto-renewal configuration."""
    enabled: bool
    institution_id: str
    plan: str
    payment_method: str
    next_renewal_date: datetime
