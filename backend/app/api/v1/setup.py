from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.setup import SetupStatusResponse, SetupRequest
from app.services.setup_service import SetupService

router = APIRouter(prefix="/setup", tags=["Setup"])


@router.get("/status", response_model=SetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)):
    """
    Check whether initial system setup has been completed.
    """
    is_completed = SetupService.is_setup_completed(db)
    company_name = SetupService.get_company_name(db)
    return SetupStatusResponse(
        is_setup=is_completed,
        company_name=company_name
    )


@router.post("", response_model=dict)
def perform_setup(
    payload: SetupRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    First-run setup wizard: sets company name and provisions initial Administrator account.
    Fails if an Administrator already exists.
    """
    client_ip = request.client.host if request.client else None
    return SetupService.perform_setup(
        db=db,
        company_name=payload.company_name,
        admin_email=payload.admin_email,
        admin_password=payload.admin_password,
        ip_address=client_ip
    )
