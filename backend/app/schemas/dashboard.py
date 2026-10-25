from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class HRDashboardResponse(BaseModel):
    headcount: int
    present_today: int
    on_leave_today: int
    late_today: int
    pending_approvals: int
    attendance_rate: float
    late_percentage: float
    attendance_trend: list[dict[str, Any]]
    absenteeism_by_dept: list[dict[str, Any]]
    leave_by_type: list[dict[str, Any]]
    top_late_comers: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class AdminDashboardResponse(BaseModel):
    headcount: int
    attrition_ytd: float
    payroll_cost: float
    average_salary: float
    headcount_by_dept: list[dict[str, Any]]
    payroll_cost_by_dept: list[dict[str, Any]]
    gender_distribution: list[dict[str, Any]]
    tenure_distribution: list[dict[str, Any]]
    recent_audit_logs: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class EmployeeDashboardResponse(BaseModel):
    employee_id: int
    employee_name: str
    hours_this_week: float
    standard_weekly_hours: float = 40.0
    late_count_this_month: int
    leave_balances: list[dict[str, Any]]
    last_payslip: Optional[dict[str, Any]] = None
    recent_announcements: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)
