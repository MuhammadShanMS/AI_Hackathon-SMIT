from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.models.models import User, UserRole
from app.schemas.comms import (
    AnnouncementCreate, AnnouncementResponse, NotificationResponse
)
from app.services.comms_service import CommsService

router = APIRouter(tags=["Comms"])


# --- Announcements ---
@router.post("/announcements", response_model=AnnouncementResponse)
def create_announcement(
    payload: AnnouncementCreate,
    request: Request,
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR)),
    db: Session = Depends(get_db)
):
    """
    Publish company announcement:
    - Admin and HR only (Employees cannot post)
    """
    client_ip = request.client.host if request.client else None
    return CommsService.create_announcement(db, actor, payload, ip_address=client_ip)


@router.get("/announcements", response_model=list[AnnouncementResponse])
def list_announcements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View all company announcements (available to all authenticated users).
    """
    return CommsService.list_announcements(db)


# --- Notifications ---
@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List notifications for currently authenticated user.
    """
    return CommsService.list_notifications(db, current_user)


@router.patch("/notifications/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark an in-app notification as read.
    """
    return CommsService.mark_as_read(db, current_user, notification_id)


@router.post("/notifications/read-all", response_model=dict)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications for current user as read.
    """
    return CommsService.mark_all_as_read(db, current_user)
