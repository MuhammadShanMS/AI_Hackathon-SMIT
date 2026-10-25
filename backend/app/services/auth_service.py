from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import verify_password, hash_password, create_access_token
from app.models.models import User
from app.services.audit_service import AuditService


class AuthService:
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            return None
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated. Contact administrator."
            )
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_user_token(user: User) -> dict:
        employee_id = user.employee.id if user.employee else None
        token_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "must_change_password": user.must_change_password,
            "employee_id": employee_id
        }
        access_token = create_access_token(token_payload)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role,
            "must_change_password": user.must_change_password,
            "user_id": user.id,
            "employee_id": employee_id
        }

    @staticmethod
    def change_password(
        db: Session,
        user: User,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> dict:
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect."
            )
        if current_password == new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as the current password."
            )

        before_state = {"must_change_password": user.must_change_password}
        user.hashed_password = hash_password(new_password)
        user.must_change_password = False
        db.commit()

        AuditService.log(
            db=db,
            actor=user,
            action="CHANGE_PASSWORD",
            entity="User",
            entity_id=user.id,
            before=before_state,
            after={"must_change_password": False},
            ip_address=ip_address
        )

        return {"message": "Password changed successfully. You may now access all features."}
