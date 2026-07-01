"""Student models."""
from pydantic import BaseModel, model_validator
from typing import Optional


class StudentBase(BaseModel):
    registration_number: Optional[str] = None
    reg_number: Optional[str] = None
    name: str
    institution_id: str

    @model_validator(mode="after")
    def normalize_registration(self):
        if not self.registration_number and self.reg_number:
            self.registration_number = self.reg_number
        return self


class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    id: str
    created_at: Optional[str] = None
