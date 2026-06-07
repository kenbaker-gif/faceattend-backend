"""Student models."""
from pydantic import BaseModel
from typing import Optional

class StudentBase(BaseModel):
    registration_number: str
    name: str
    institution_id: str

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: str
    created_at: Optional[str] = None
