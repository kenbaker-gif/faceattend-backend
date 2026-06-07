"""Attendance models."""
from pydantic import BaseModel
from typing import Optional

class AttendanceRecord(BaseModel):
    student_id: str
    session_id: str
    coordinator_id: str
    institution_id: str
    confidence: Optional[float] = None

class AttendanceResponse(AttendanceRecord):
    id: str
    marked_at: str
