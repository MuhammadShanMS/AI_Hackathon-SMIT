from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.models.models import User, UserRole
from app.schemas.employee import (
    EmployeeRegisterRequest, EmployeeRegisterResponse,
    EmployeeDirectoryResponse, Employee360Profile,
    EmployeeSelfUpdate, EmployeeHRUpdate
)
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("", response_model=EmployeeRegisterResponse)
def register_employee(
    payload: EmployeeRegisterRequest,
    request: Request,
    hr_user: User = Depends(require_roles(UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    HR registers an employee:
    - Generates user account with temporary password & must_change_password=True
    - Returns temporary password once
    - Auto-provisions LeaveBalances for all active leave types
    """
    client_ip = request.client.host if request.client else None
    return EmployeeService.register_employee(db, hr_user, payload, ip_address=client_ip)


@router.get("", response_model=EmployeeDirectoryResponse)
def list_employees(
    search: Optional[str] = Query(None, description="Search by name, employee code, or email"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by active/inactive"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Directory with server-side search, filters, and pagination.
    Employees cannot see others' salary information.
    """
    return EmployeeService.list_employees(
        db=db,
        current_user=current_user,
        search=search,
        department_id=department_id,
        status_filter=status,
        limit=limit,
        offset=offset
    )


@router.get("/{employee_id}", response_model=Employee360Profile)
def get_employee_profile(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Employee 360 profile:
    - Employees can only read their own profile (403 otherwise).
    - HR and Admin can view any profile.
    """
    return EmployeeService.get_employee_360(db, current_user, employee_id)


@router.patch("/{employee_id}/self", response_model=Employee360Profile)
def update_self_profile(
    employee_id: int,
    payload: EmployeeSelfUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Self-service profile update:
    - Employee can edit only their own phone and address.
    """
    client_ip = request.client.host if request.client else None
    return EmployeeService.update_self_profile(db, current_user, employee_id, payload, ip_address=client_ip)


@router.patch("/{employee_id}", response_model=Employee360Profile)
def update_employee_by_hr(
    employee_id: int,
    payload: EmployeeHRUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    HR edits employee profile:
    - Salary structure and job details are editable by HR only.
    - Admin has view-only rights.
    """
    client_ip = request.client.host if request.client else None
    return EmployeeService.update_employee_by_hr(db, current_user, employee_id, payload, ip_address=client_ip)
