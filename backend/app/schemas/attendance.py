from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.models import ApprovalStatus


# --- Check In / Out ---
class CheckInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    faces_detected: Optional[int] = None
    check_in_method: str = "NORMAL"  # NORMAL or FACE_DETECTION


class CheckOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    status: str
    work_hours: float
    check_in_method: str = "NORMAL"

    model_config = ConfigDict(from_attributes=True)


# --- Monthly Calendar ---
class DailyCalendarItem(BaseModel):
    date: date
    day_name: str
    status: str  # PRESENT, LATE, HALF_DAY, MISSING_CHECKOUT, ON_LEAVE, ABSENT, WEEKEND, HOLIDAY, NOT_EMPLOYED, UPCOMING
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    work_hours: float = 0.0
    note: Optional[str] = None


class MonthlyCalendarResponse(BaseModel):
    employee_id: int
    employee_name: str
    year: int
    month: int
    working_days: int
    present_count: int
    late_count: int
    half_day_count: int
    absent_count: int
    on_leave_count: int
    days: list[DailyCalendarItem]


# --- Daily Attendance Board ---
class DailyBoardItem(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str
    designation_name: str
    status: str
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    work_hours: float = 0.0


class DailyBoardResponse(BaseModel):
    date: date
    total_employees: int
    present: int
    late: int
    half_day: int
    on_leave: int
    absent: int
    missing_checkout: int
    roster: list[DailyBoardItem]


# --- Corrections ---
class CorrectionCreate(BaseModel):
    date: date
    requested_check_in: Optional[datetime] = None
    requested_check_out: Optional[datetime] = None
    reason: str = Field(..., min_length=5, max_length=500)


class CorrectionReview(BaseModel):
    status: ApprovalStatus  # APPROVED or REJECTED
    comment: str = Field(..., min_length=2, max_length=500)


class CorrectionResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    requested_check_in: Optional[datetime] = None
    requested_check_out: Optional[datetime] = None
    reason: str
    status: str
    reviewed_by: Optional[int] = None
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
