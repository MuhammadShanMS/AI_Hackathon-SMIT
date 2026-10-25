from pydantic import BaseModel, EmailStr, Field


class SetupStatusResponse(BaseModel):
    is_setup: bool          # true only when admin AND company settings both exist
    company_name: str | None = None


class SetupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=128)
