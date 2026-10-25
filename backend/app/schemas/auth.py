from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.models import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    must_change_password: bool
    user_id: int
    employee_id: Optional[int] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserMeResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    must_change_password: bool
    employee_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
