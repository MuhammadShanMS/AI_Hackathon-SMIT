from datetime import date
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- Company Settings ---
class CompanySettingsResponse(BaseModel):
    id: int
    company_name: str
    office_start_time: str
    grace_period_minutes: int
    half_day_hours_threshold: float
    weekend_days: str
    office_latitude: Optional[float] = None
    office_longitude: Optional[float] = None
    office_radius_meters: float

    model_config = ConfigDict(from_attributes=True)


class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    office_start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    grace_period_minutes: Optional[int] = Field(None, ge=0, le=120)
    half_day_hours_threshold: Optional[float] = Field(None, ge=1.0, le=12.0)
    weekend_days: Optional[str] = Field(None, max_length=50)
    office_latitude: Optional[float] = None
    office_longitude: Optional[float] = None
    office_radius_meters: Optional[float] = Field(None, ge=10.0, le=10000.0)


# --- Departments ---
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Designations ---
class DesignationCreate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def sync_name_and_title(cls, data: Any):
        if isinstance(data, dict):
            val = data.get("name") or data.get("title")
            if val:
                data["name"] = val
                data["title"] = val
        return data


class DesignationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def sync_name_and_title(cls, data: Any):
        if isinstance(data, dict):
            val = data.get("name") or data.get("title")
            if val:
                data["name"] = val
                data["title"] = val
        return data


class DesignationResponse(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def populate_title(self):
        if not self.title:
            self.title = self.name
        return self

    model_config = ConfigDict(from_attributes=True)


# --- Leave Types ---
class LeaveTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    yearly_quota: int = Field(..., ge=0, le=365)
    is_paid: bool = True


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    yearly_quota: Optional[int] = Field(None, ge=0, le=365)
    is_paid: Optional[bool] = None


class LeaveTypeResponse(BaseModel):
    id: int
    name: str
    yearly_quota: int
    is_paid: bool

    model_config = ConfigDict(from_attributes=True)


# --- Public Holidays ---
class HolidayCreate(BaseModel):
    date: date
    name: str = Field(..., min_length=2, max_length=100)


class HolidayUpdate(BaseModel):
    date: Optional[date] = None
    name: Optional[str] = Field(None, min_length=2, max_length=100)


class HolidayResponse(BaseModel):
    id: int
    date: date
    name: str

    model_config = ConfigDict(from_attributes=True)
