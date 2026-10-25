from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_roles
from app.models.models import User, UserRole
from app.schemas.org import (
    CompanySettingsResponse, CompanySettingsUpdate,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    DesignationCreate, DesignationUpdate, DesignationResponse,
    LeaveTypeCreate, LeaveTypeUpdate, LeaveTypeResponse,
    HolidayCreate, HolidayUpdate, HolidayResponse
)
from app.services.org_service import OrgService

router = APIRouter(prefix="/org", tags=["Org Setup"])


# --- Company Settings ---
@router.get("/settings", response_model=CompanySettingsResponse)
def get_company_settings(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    return OrgService.get_settings(db)


@router.put("/settings", response_model=CompanySettingsResponse)
def update_company_settings(
    payload: CompanySettingsUpdate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.update_settings(db, admin_user, payload, ip_address=client_ip)


# --- Departments ---
@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    return OrgService.list_departments(db)


@router.post("/departments", response_model=DepartmentResponse)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.create_department(db, admin_user, payload, ip_address=client_ip)


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.update_department(db, admin_user, dept_id, payload, ip_address=client_ip)


@router.delete("/departments/{dept_id}", response_model=dict)
def delete_department(
    dept_id: int,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.delete_department(db, admin_user, dept_id, ip_address=client_ip)


# --- Designations ---
@router.get("/designations", response_model=list[DesignationResponse])
def list_designations(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    return OrgService.list_designations(db)


@router.post("/designations", response_model=DesignationResponse)
def create_designation(
    payload: DesignationCreate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.create_designation(db, admin_user, payload, ip_address=client_ip)


@router.put("/designations/{desig_id}", response_model=DesignationResponse)
def update_designation(
    desig_id: int,
    payload: DesignationUpdate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.update_designation(db, admin_user, desig_id, payload, ip_address=client_ip)


@router.delete("/designations/{desig_id}", response_model=dict)
def delete_designation(
    desig_id: int,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.delete_designation(db, admin_user, desig_id, ip_address=client_ip)


# --- Leave Types ---
@router.get("/leave-types", response_model=list[LeaveTypeResponse])
def list_leave_types(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    return OrgService.list_leave_types(db)


@router.post("/leave-types", response_model=LeaveTypeResponse)
def create_leave_type(
    payload: LeaveTypeCreate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.create_leave_type(db, admin_user, payload, ip_address=client_ip)


@router.put("/leave-types/{lt_id}", response_model=LeaveTypeResponse)
def update_leave_type(
    lt_id: int,
    payload: LeaveTypeUpdate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.update_leave_type(db, admin_user, lt_id, payload, ip_address=client_ip)


@router.delete("/leave-types/{lt_id}", response_model=dict)
def delete_leave_type(
    lt_id: int,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.delete_leave_type(db, admin_user, lt_id, ip_address=client_ip)


# --- Public Holidays ---
@router.get("/holidays", response_model=list[HolidayResponse])
def list_holidays(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    return OrgService.list_holidays(db)


@router.post("/holidays", response_model=HolidayResponse)
def create_holiday(
    payload: HolidayCreate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.create_holiday(db, admin_user, payload, ip_address=client_ip)


@router.put("/holidays/{h_id}", response_model=HolidayResponse)
def update_holiday(
    h_id: int,
    payload: HolidayUpdate,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.update_holiday(db, admin_user, h_id, payload, ip_address=client_ip)


@router.delete("/holidays/{h_id}", response_model=dict)
def delete_holiday(
    h_id: int,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    return OrgService.delete_holiday(db, admin_user, h_id, ip_address=client_ip)
