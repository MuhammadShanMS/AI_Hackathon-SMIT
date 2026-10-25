from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.models import ApprovalStatus


class LeaveApplyRequest(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = Field(None, max_length=500)


class LeaveBalanceResponse(BaseModel):
    leave_type_id: int
    leave_type_name: str
    yearly_quota: int
    used_days: float
    remaining_days: float
    is_paid: bool

    model_config = ConfigDict(from_attributes=True)


class LeaveRequestResponse(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    leave_type_id: int
    leave_type_name: str
    start_date: date
    end_date: date
    working_days_count: int
    reason: Optional[str] = None
    status: str
    reviewed_by: Optional[int] = None
    review_comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveReviewRequest(BaseModel):
    status: ApprovalStatus  # APPROVED or REJECTED
    comment: Optional[str] = Field(None, max_length=500)
