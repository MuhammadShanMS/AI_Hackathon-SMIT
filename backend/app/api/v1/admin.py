from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_roles
from app.models.models import User, UserRole
from app.schemas.admin import CreateHRRequest, UpdateUserStatusRequest, ResetPasswordRequest, AdminUserResponse
from app.schemas.auth import MessageResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to view all system users with their roles and status.
    """
    return AdminService.get_all_users(db)


@router.post("/users/hr", response_model=AdminUserResponse)
def create_hr_account(
    payload: CreateHRRequest,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to provision a new HR account with forced initial password rotation.
    """
    client_ip = request.client.host if request.client else None
    hr_user = AdminService.create_hr(
        db=db,
        admin_user=admin_user,
        email=payload.email,
        password=payload.password,
        ip_address=client_ip
    )
    return hr_user


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
def update_user_status(
    user_id: int,
    payload: UpdateUserStatusRequest,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to activate or deactivate a user account.
    """
    client_ip = request.client.host if request.client else None
    updated_user = AdminService.set_user_status(
        db=db,
        admin_user=admin_user,
        user_id=user_id,
        is_active=payload.is_active,
        ip_address=client_ip
    )
    return updated_user


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
def reset_user_password(
    user_id: int,
    payload: ResetPasswordRequest,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to issue a temporary password, forcing the user to change it on next login.
    """
    client_ip = request.client.host if request.client else None
    AdminService.reset_password(
        db=db,
        admin_user=admin_user,
        user_id=user_id,
        temporary_password=payload.temporary_password,
        ip_address=client_ip
    )
    return MessageResponse(message=f"Password for user {user_id} successfully reset. Temporary flag enabled.")
