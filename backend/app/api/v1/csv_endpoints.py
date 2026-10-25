from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_roles
from app.models.models import User, UserRole
from app.schemas.csv_schemas import CSVImportResponse
from app.services.csv_service import CSVService

router = APIRouter(prefix="/employees/csv", tags=["Employee CSV"])


@router.get("/export")
def export_employees_csv(
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Export all employee records as a CSV spreadsheet (HR/Admin only).
    """
    csv_content, filename = CSVService.export_employees(db, actor)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import", response_model=CSVImportResponse)
async def import_employees_csv(
    request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(True, description="When True, validates without committing changes to DB"),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Bulk import employee records from a CSV file:
    - Validates required fields, unique email/code, known department, ISO date, salary > 0
    - If dry_run=True: returns row-level validation errors without writing to DB
    - If dry_run=False and valid: registers users, employee profiles, and provisions leave balances
    """
    file_bytes = await file.read()
    csv_text = file_bytes.decode("utf-8-sig", errors="replace")
    client_ip = request.client.host if request.client else None
    return CSVService.import_employees(
        db=db,
        actor=actor,
        csv_content=csv_text,
        dry_run=dry_run,
        ip_address=client_ip
    )
