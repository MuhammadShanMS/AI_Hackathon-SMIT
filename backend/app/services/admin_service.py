from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.models import User, UserRole
from app.services.audit_service import AuditService


class AdminService:
    @staticmethod
    def get_all_users(db: Session) -> list[User]:
        return db.query(User).order_by(User.id.asc()).all()

    @staticmethod
    def create_hr(
        db: Session,
        admin_user: User,
        email: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> User:
        clean_email = email.strip().lower()
        existing = db.query(User).filter(User.email == clean_email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        hr_user = User(
            email=clean_email,
            hashed_password=hash_password(password),
            role=UserRole.HR,
            is_active=True,
            must_change_password=True
        )
        db.add(hr_user)
        db.commit()
        db.refresh(hr_user)

        AuditService.log(
            db=db,
            actor=admin_user,
            action="CREATE",
            entity="User",
            entity_id=hr_user.id,
            after={"email": hr_user.email, "role": hr_user.role.value, "must_change_password": True},
            ip_address=ip_address
        )
        return hr_user

    @staticmethod
    def set_user_status(
        db: Session,
        admin_user: User,
        user_id: int,
        is_active: bool,
        ip_address: Optional[str] = None
    ) -> User:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        if target.id == admin_user.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate their own account."
            )

        before_state = {"is_active": target.is_active}
        target.is_active = is_active
        db.commit()
        db.refresh(target)

        action = "ACTIVATE" if is_active else "DEACTIVATE"
        AuditService.log(
            db=db,
            actor=admin_user,
            action=action,
            entity="User",
            entity_id=target.id,
            before=before_state,
            after={"is_active": is_active},
            ip_address=ip_address
        )
        return target

    @staticmethod
    def reset_password(
        db: Session,
        admin_user: User,
        user_id: int,
        temporary_password: str,
        ip_address: Optional[str] = None
    ) -> User:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        before_state = {"must_change_password": target.must_change_password}
        target.hashed_password = hash_password(temporary_password)
        target.must_change_password = True
        db.commit()
        db.refresh(target)

        AuditService.log(
            db=db,
            actor=admin_user,
            action="RESET_PASSWORD",
            entity="User",
            entity_id=target.id,
            before=before_state,
            after={"must_change_password": True},
            ip_address=ip_address
        )
        return target
