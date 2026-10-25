from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user_flexible(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Decodes the token and retrieves the active user.
    Allows users with must_change_password=True (specifically for password-change endpoint).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    return user


def get_current_user(
    current_user: User = Depends(get_current_user_flexible)
) -> User:
    """
    Standard user dependency that enforces must_change_password=False.
    Blocks any access until temporary password is changed.
    """
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required before accessing system resources."
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    """
    Factory dependency to enforce server-side role-based access control (RBAC).
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of {[r.value for r in allowed_roles]} roles."
            )
        return current_user

    return role_checker


def verify_employee_scope(target_employee_id: int, current_user: User) -> None:
    """
    Server-side scope guard ensuring an EMPLOYEE can only view/modify their own employee records.
    ADMIN and HR have system-wide visibility.
    """
    if current_user.role == UserRole.EMPLOYEE:
        if not current_user.employee or current_user.employee.id != target_employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access records belonging to your own employee ID."
            )


def get_scoped_employee_id(requested_id: Optional[int], current_user: User) -> Optional[int]:
    """
    Sanitizes employee_id query parameters. If role is EMPLOYEE, forces target to current user's employee_id.
    """
    if current_user.role == UserRole.EMPLOYEE:
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not associated with an employee profile."
            )
        return current_user.employee.id
    return requested_id
