"""Institution models."""
from pydantic import BaseModel
from typing import Optional

class InstitutionBase(BaseModel):
    name: str
    admin_email: str

class InstitutionResponse(InstitutionBase):
    id: str
    plans: str
    is_active: bool
    trial_ends_at: Optional[str] = None
    subscription_expires_at: Optional[str] = None
