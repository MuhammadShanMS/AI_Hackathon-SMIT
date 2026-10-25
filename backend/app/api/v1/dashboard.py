from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.models.models import User, UserRole
from app.schemas.dashboard import (
    HRDashboardResponse, AdminDashboardResponse, EmployeeDashboardResponse
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])


@router.get("/hr", response_model=HRDashboardResponse)
def get_hr_dashboard(
    start_date: Optional[date] = Query(None, description="Start date for attendance trend and metrics"),
    end_date: Optional[date] = Query(None, description="End date for attendance trend and metrics"),
    department_id: Optional[int] = Query(None, description="Filter metrics by department"),
    current_user: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Server-side aggregated HR dashboard:
    - Headcount, present today, on leave today, late today, pending approvals
    - Attendance rate & Late percentage formulas
    - Attendance trend, absenteeism by department, leave utilization by type, top 5 late comers
    """
    return DashboardService.get_hr_dashboard(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id
    )


@router.get("/admin", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Server-side aggregated Admin dashboard:
    - Headcount, attrition YTD, payroll cost, average salary
    - Headcount by dept, payroll cost by dept, gender & tenure distributions
    - Last 10 immutable audit entries
    - HR cannot access (403)
    """
    return DashboardService.get_admin_dashboard(db=db, current_user=current_user)


@router.get("/employee", response_model=EmployeeDashboardResponse)
def get_employee_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Employee personal dashboard:
    - Scoped strictly to current user's employee record
    - Hours this week vs 40h standard, late count this month, leave balances, last payslip, announcements
    """
    return DashboardService.get_employee_dashboard(db=db, current_user=current_user)
