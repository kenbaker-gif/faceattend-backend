"""Payment models."""
from pydantic import BaseModel
from typing import Optional

class PaymentRequest(BaseModel):
    institution_id: str
    plan: str
    amount: float
    currency: str = "KES"

class PaymentResponse(BaseModel):
    order_tracking_id: str
    merchant_reference: str
    redirect_url: Optional[str] = None
    status: str
