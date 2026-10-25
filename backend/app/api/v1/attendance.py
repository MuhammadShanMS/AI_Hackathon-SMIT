from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.models.models import User, UserRole, ApprovalStatus
from app.schemas.attendance import (
    CheckInRequest, CheckOutRequest, AttendanceResponse,
    MonthlyCalendarResponse, DailyBoardResponse,
    CorrectionCreate, CorrectionReview, CorrectionResponse
)
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/check-in", response_model=AttendanceResponse)
def check_in(
    payload: Optional[CheckInRequest] = Body(default=None),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clock in for today:
    - Server stamps current timestamp.
    - Second check-in on the same day raises 409 Conflict.
    - Status set to LATE if checking in after office_start_time + grace_period_minutes.
    """
    if payload is None:
        payload = CheckInRequest()
    client_ip = request.client.host if request and request.client else None
    return AttendanceService.check_in(db, current_user, payload, ip_address=client_ip)


@router.post("/check-out", response_model=AttendanceResponse)
def check_out(
    payload: Optional[CheckOutRequest] = Body(default=None),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clock out for today:
    - Server stamps current timestamp.
    - Computes work hours.
    - Status set to HALF_DAY if total work hours < half_day_hours_threshold.
    """
    if payload is None:
        payload = CheckOutRequest()
    client_ip = request.client.host if request and request.client else None
    return AttendanceService.check_out(db, current_user, payload, ip_address=client_ip)


@router.get("/calendar", response_model=MonthlyCalendarResponse)
def get_monthly_calendar(
    employee_id: int = Query(..., description="Target employee ID"),
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Monthly attendance calendar:
    - Employee can only view their own calendar (403 otherwise).
    - HR and Admin can view any employee's calendar.
    - ABSENT is calculated, not stored: working day, no record, no approved leave.
    """
    return AttendanceService.get_monthly_calendar(db, current_user, employee_id, year, month)


@router.get("/daily-board", response_model=DailyBoardResponse)
def get_daily_attendance_board(
    date_val: date = Query(default_factory=date.today, alias="date"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    Daily attendance overview board for HR and Administrators:
    - Aggregate metrics and roster for all active employees on the specified date.
    """
    return AttendanceService.get_daily_board(db, current_user, date_val)


# --- Attendance Corrections ---
@router.post("/corrections", response_model=CorrectionResponse)
def request_attendance_correction(
    payload: CorrectionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Employee requests an attendance correction with a reason.
    """
    client_ip = request.client.host if request.client else None
    return AttendanceService.request_correction(db, current_user, payload, ip_address=client_ip)


@router.get("/corrections", response_model=list[CorrectionResponse])
def list_attendance_corrections(
    status_filter: Optional[ApprovalStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List attendance corrections:
    - Employees see only their own requests.
    - HR and Admin see all requests.
    """
    return AttendanceService.list_corrections(db, current_user, status_filter)


@router.patch("/corrections/{correction_id}/review", response_model=CorrectionResponse)
def review_attendance_correction(
    correction_id: int,
    payload: CorrectionReview,
    request: Request,
    hr_user: User = Depends(require_roles(UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    HR reviews attendance correction:
    - Approves or rejects with a comment.
    - On approval, updates the underlying attendance record with recomputed work hours & status.
    - Creates an in-app notification for the employee.
    """
    client_ip = request.client.host if request.client else None
    return AttendanceService.review_correction(db, hr_user, correction_id, payload, ip_address=client_ip)
