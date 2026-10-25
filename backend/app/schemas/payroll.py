from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PayrollCreateDraftRequest(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)


class PayslipResponse(BaseModel):
    id: int
    payroll_run_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str
    working_days_in_month: int
    worked_days: float
    basic_salary: float
    hra: float
    medical_allowance: float
    gross_salary: float
    daily_rate: float
    absent_days: float
    unpaid_leave_days: float
    half_days: int
    deductions: float
    annual_gross: float
    annual_tax: float
    monthly_tax: float
    net_salary: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollRunResponse(BaseModel):
    id: int
    year: int
    month: int
    status: str
    total_payout: float
    finalized_by: Optional[int] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    payslip_count: int
    payslips: Optional[list[PayslipResponse]] = None

    model_config = ConfigDict(from_attributes=True)
