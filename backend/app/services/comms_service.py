from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import Announcement, Notification, User, UserRole
from app.schemas.comms import AnnouncementCreate, AnnouncementResponse, NotificationResponse
from app.services.audit_service import AuditService


class CommsService:
    # --- Announcements ---
    @staticmethod
    def create_announcement(
        db: Session,
        actor: User,
        data: AnnouncementCreate,
        ip_address: Optional[str] = None
    ) -> AnnouncementResponse:
        # Rule: Admin and HR post
        if actor.role not in (UserRole.ADMIN, UserRole.HR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only Administrators and HR can publish company announcements."
            )

        ann = Announcement(
            title=data.title.strip(),
            body=data.body.strip(),
            created_by=actor.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(ann)
        db.commit()
        db.refresh(ann)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_ANNOUNCEMENT",
            entity="Announcement",
            entity_id=ann.id,
            after={"title": ann.title},
            ip_address=ip_address
        )

        author_name = "Admin" if actor.role == UserRole.ADMIN else "HR"
        if actor.employee:
            author_name = f"{actor.employee.first_name} {actor.employee.last_name}"

        return AnnouncementResponse(
            id=ann.id,
            title=ann.title,
            body=ann.body,
            created_by=ann.created_by,
            author_name=author_name,
            created_at=ann.created_at
        )

    @staticmethod
    def list_announcements(db: Session) -> list[AnnouncementResponse]:
        announcements = db.query(Announcement).order_by(Announcement.created_at.desc()).all()
        results = []
        for ann in announcements:
            author_name = "Company Admin"
            if ann.author:
                if ann.author.employee:
                    author_name = f"{ann.author.employee.first_name} {ann.author.employee.last_name}"
                elif ann.author.role == UserRole.ADMIN:
                    author_name = "Administrator"
                elif ann.author.role == UserRole.HR:
                    author_name = "HR Department"
            results.append(
                AnnouncementResponse(
                    id=ann.id,
                    title=ann.title,
                    body=ann.body,
                    created_by=ann.created_by,
                    author_name=author_name,
                    created_at=ann.created_at
                )
            )
        return results

    # --- Notifications ---
    @staticmethod
    def list_notifications(db: Session, current_user: User) -> list[NotificationResponse]:
        notifs = db.query(Notification).filter(
            Notification.user_id == current_user.id
        ).order_by(Notification.created_at.desc()).all()

        return [
            NotificationResponse(
                id=n.id,
                user_id=n.user_id,
                message=n.message,
                is_read=n.is_read,
                created_at=n.created_at
            )
            for n in notifs
        ]

    @staticmethod
    def mark_as_read(db: Session, current_user: User, notif_id: int) -> dict:
        notif = db.query(Notification).filter(
            Notification.id == notif_id,
            Notification.user_id == current_user.id
        ).first()
        if not notif:
            raise HTTPException(status_code=404, detail="Notification not found.")

        notif.is_read = True
        db.commit()
        return {"message": "Notification marked as read."}

    @staticmethod
    def mark_all_as_read(db: Session, current_user: User) -> dict:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).update({"is_read": True})
        db.commit()
        return {"message": "All notifications marked as read."}
