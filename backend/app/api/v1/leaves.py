from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.models.models import User, UserRole, ApprovalStatus
from app.schemas.leave import (
    LeaveApplyRequest, LeaveBalanceResponse, LeaveRequestResponse, LeaveReviewRequest
)
from app.services.leave_service import LeaveService

router = APIRouter(prefix="/leaves", tags=["Leaves"])


@router.post("", response_model=LeaveRequestResponse)
def apply_leave(
    payload: LeaveApplyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Employee submits leave application:
    - Working days calculated skipping weekends and public holidays
    - Overlap with PENDING/APPROVED leaves raises 422
    - Over-balance raises 422 (unpaid is unlimited)
    """
    client_ip = request.client.host if request.client else None
    return LeaveService.apply_leave(db, current_user, payload, ip_address=client_ip)


@router.get("/balances", response_model=list[LeaveBalanceResponse])
def get_leave_balances(
    employee_id: Optional[int] = Query(None, description="Employee ID (Admin/HR only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get yearly leave balance quota, used days, and remaining balance.
    Employees see only their own balances.
    """
    return LeaveService.get_balances(db, current_user, employee_id)


@router.get("", response_model=list[LeaveRequestResponse])
def list_leaves(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID (HR/Admin)"),
    status: Optional[ApprovalStatus] = Query(None, description="Filter by approval status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List leave requests:
    - Employees see only their own applications
    - HR and Admin see all applications
    """
    return LeaveService.list_leaves(db, current_user, employee_id, status)


@router.post("/{leave_id}/cancel", response_model=dict)
def cancel_leave(
    leave_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Employee cancels their pending leave request.
    """
    client_ip = request.client.host if request.client else None
    return LeaveService.cancel_leave(db, current_user, leave_id, ip_address=client_ip)


@router.patch("/{leave_id}/review", response_model=LeaveRequestResponse)
def review_leave(
    leave_id: int,
    payload: LeaveReviewRequest,
    request: Request,
    hr_user: User = Depends(require_roles(UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    HR reviews leave request:
    - On approval, deducts leave balance and marks attendance dates as ON_LEAVE
    - Creates an in-app notification for the employee
    - Admin has view-only rights
    """
    client_ip = request.client.host if request.client else None
    return LeaveService.review_leave(db, hr_user, leave_id, payload, ip_address=client_ip)
