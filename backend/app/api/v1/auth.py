from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_user_flexible
from app.models.models import User
from app.schemas.auth import LoginRequest, TokenResponse, ChangePasswordRequest, UserMeResponse, MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and issue JWT access token.
    """
    user = AuthService.authenticate(db=db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    return AuthService.create_user_token(user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    Change user password. Allows users with must_change_password=True to rotate temporary password.
    """
    client_ip = request.client.host if request.client else None
    result = AuthService.change_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=client_ip
    )
    return MessageResponse(**result)


@router.get("/me", response_model=UserMeResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve profile of currently authenticated user.
    Enforces must_change_password=False (blocked if password change is pending).
    """
    emp = current_user.employee
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        must_change_password=current_user.must_change_password,
        employee_id=emp.id if emp else None,
        first_name=emp.first_name if emp else None,
        last_name=emp.last_name if emp else None,
    )
