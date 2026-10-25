from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_roles
from app.models.models import User, UserRole
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=list[AuditLogResponse])
def get_audit_trail(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Read-only endpoint for Administrators to inspect the system audit trail.
    No update or delete operations are permitted.
    """
    logs = AuditService.get_logs(db=db, limit=limit, offset=offset)
    return logs
