from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.models import UserRole


class CreateHRRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(..., min_length=8, max_length=128)


class AdminUserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    must_change_password: bool

    model_config = ConfigDict(from_attributes=True)
