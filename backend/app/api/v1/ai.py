from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.models import User, UserRole
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    DashboardSummaryRequest,
    DashboardSummaryResponse,
    SmartLeaveRequest,
    SmartLeaveResponse,
)
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/chat", response_model=ChatResponse)
def ai_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Intelligent Workforce Assistant with server-side scoped function calling.
    Understands Roman Urdu and English. Scoped to the caller's role and data permissions.
    """
    result = AIService.chat(
        db=db,
        current_user=current_user,
        message=payload.message,
        history=payload.history,
    )
    return ChatResponse(**result)


@router.post(
    "/dashboard-summary",
    response_model=DashboardSummaryResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.HR))],
)
def ai_dashboard_summary(
    payload: DashboardSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate 3-5 concise bullet insights using ONLY the provided KPI numbers.
    Accessible to HR and Admin roles only.
    """
    result = AIService.dashboard_summary(
        current_user=current_user,
        kpi_data=payload.kpi_data,
        db=db,
    )
    return DashboardSummaryResponse(**result)


@router.post("/smart-leave", response_model=SmartLeaveResponse)
def ai_smart_leave(
    payload: SmartLeaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Parse a natural language leave sentence into a structured JSON leave request.
    Validates format and never auto-saves to database.
    """
    result = AIService.smart_leave(
        current_user=current_user,
        text=payload.text,
        db=db,
    )
    return SmartLeaveResponse(**result)
