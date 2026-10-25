from datetime import date
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LeaveBalanceSummary(BaseModel):
    leave_type_name: str
    yearly_quota: int
    used_days: float
    remaining_days: float

    model_config = ConfigDict(from_attributes=True)


class EmployeeRegisterRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field("Unspecified", max_length=20)
    department_id: int
    designation_id: int
    joining_date: Optional[date] = None
    date_of_joining: Optional[date] = None
    basic_salary: float = Field(..., ge=0.0)
    allowances: float = Field(0.0, ge=0.0)

    @model_validator(mode="before")
    @classmethod
    def sync_joining_date(cls, data: Any):
        if isinstance(data, dict):
            j_date = data.get("joining_date") or data.get("date_of_joining")
            if j_date:
                data["joining_date"] = j_date
                data["date_of_joining"] = j_date
        return data


class EmployeeRegisterResponse(BaseModel):
    id: int
    user_id: int
    employee_code: str
    email: str
    first_name: str
    last_name: str
    department_id: int
    designation_id: int
    temporary_password: str
    message: str


class EmployeeDirectoryItem(BaseModel):
    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    department_id: int
    department_name: str
    designation_id: int
    designation_name: str
    joining_date: date
    is_active: bool
    basic_salary: Optional[float] = None
    allowances: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeDirectoryResponse(BaseModel):
    total: int
    items: list[EmployeeDirectoryItem]


class Employee360Profile(BaseModel):
    id: int
    user_id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    department_id: int
    department_name: str
    designation_id: int
    designation_name: str
    joining_date: date
    exit_date: Optional[date] = None
    is_active: bool
    basic_salary: Optional[float] = None
    allowances: Optional[float] = None
    leave_balances: list[LeaveBalanceSummary] = []

    model_config = ConfigDict(from_attributes=True)


class EmployeeSelfUpdate(BaseModel):
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)


class EmployeeHRUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    joining_date: Optional[date] = None
    exit_date: Optional[date] = None
    basic_salary: Optional[float] = Field(None, ge=0.0)
    allowances: Optional[float] = Field(None, ge=0.0)
