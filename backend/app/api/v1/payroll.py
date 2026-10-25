import io
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.models.models import User, UserRole
from app.schemas.payroll import (
    PayrollCreateDraftRequest, PayrollRunResponse, PayslipResponse
)
from app.services.payroll_service import PayrollService

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.post("/draft", response_model=PayrollRunResponse)
def create_payroll_draft(
    payload: PayrollCreateDraftRequest,
    request: Request,
    hr_user: User = Depends(require_roles(UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    HR generates a monthly DRAFT payroll run:
    - Gross = 1.5 * Basic
    - Per-day rate = Gross / Working days in month
    - Formulaic deductions for Absent, Unpaid Leave, Half-day, and Prorating
    - 5-tier statutory annual income tax slab
    """
    client_ip = request.client.host if request.client else None
    return PayrollService.create_monthly_draft(db, hr_user, payload, ip_address=client_ip)


@router.get("/runs", response_model=list[PayrollRunResponse])
def list_payroll_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List monthly payroll runs.
    """
    return PayrollService.list_payroll_runs(db, current_user)


@router.get("/runs/{run_id}", response_model=PayrollRunResponse)
def get_payroll_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get payroll run details with itemized payslips:
    - Employees see only their own payslip item
    - HR and Admin see all payslips
    """
    return PayrollService.get_payroll_run(db, current_user, run_id)


@router.post("/runs/{run_id}/finalize", response_model=PayrollRunResponse)
def finalize_payroll_run(
    run_id: int,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Admin finalizes a payroll run:
    - Locks the run against further edits
    - Generates in-app notifications to all employees
    - HR cannot finalize (403)
    """
    client_ip = request.client.host if request.client else None
    return PayrollService.finalize_payroll(db, admin_user, run_id, ip_address=client_ip)


@router.get("/payslips/{payslip_id}/pdf")
def download_payslip_pdf(
    payslip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download official payslip PDF:
    - Employees can only download their own payslip (403 otherwise)
    - HR and Admin can download any payslip
    """
    pdf_bytes, filename = PayrollService.generate_payslip_pdf(db, current_user, payslip_id)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
