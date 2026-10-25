from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Numeric, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Enum
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    HR = "HR"
    EMPLOYEE = "EMPLOYEE"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    LATE = "LATE"
    HALF_DAY = "HALF_DAY"
    MISSING_CHECKOUT = "MISSING_CHECKOUT"
    ON_LEAVE = "ON_LEAVE"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PayrollStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class CompanySettings(Base, TimestampMixin):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    office_start_time = Column(String(10), default="09:00", nullable=False)
    grace_period_minutes = Column(Integer, default=15, nullable=False)
    half_day_hours_threshold = Column(Float, default=5.0, nullable=False)
    weekend_days = Column(String(50), default="5,6", nullable=False)  # 5=Sat, 6=Sun
    office_latitude = Column(Float, nullable=True)
    office_longitude = Column(Float, nullable=True)
    office_radius_meters = Column(Float, default=100.0, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)

    employee = relationship("Employee", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    employees = relationship("Employee", back_populates="department")


class Designation(Base, TimestampMixin):
    __tablename__ = "designations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    employees = relationship("Employee", back_populates="designation")


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    gender = Column(String(20), nullable=True, default="Unspecified")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    designation_id = Column(Integer, ForeignKey("designations.id"), nullable=False)
    joining_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=True)
    basic_salary = Column(Numeric(12, 2), default=0.00, nullable=False)
    allowances = Column(Numeric(12, 2), default=0.00, nullable=False)

    user = relationship("User", back_populates="employee")
    department = relationship("Department", back_populates="employees")
    designation = relationship("Designation", back_populates="employees")
    attendances = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    leave_balances = relationship("LeaveBalance", back_populates="employee", cascade="all, delete-orphan")
    attendance_corrections = relationship("AttendanceCorrection", back_populates="employee", cascade="all, delete-orphan")
    payslips = relationship("Payslip", back_populates="employee")


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_employee_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    check_in_lat = Column(Float, nullable=True)
    check_in_lng = Column(Float, nullable=True)
    check_out_lat = Column(Float, nullable=True)
    check_out_lng = Column(Float, nullable=True)
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)
    work_hours = Column(Float, default=0.0, nullable=False)
    check_in_method = Column(String(30), default="NORMAL", nullable=False)  # NORMAL or FACE_DETECTION

    employee = relationship("Employee", back_populates="attendances")


class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g., ANNUAL, SICK, CASUAL, UNPAID
    yearly_quota = Column(Integer, default=0, nullable=False)
    is_paid = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_emp_leave_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    year = Column(Integer, nullable=False)
    used_days = Column(Float, default=0.0, nullable=False)

    employee = relationship("Employee", back_populates="leave_balances")
    leave_type = relationship("LeaveType")


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    working_days_count = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="leave_requests")
    leave_type = relationship("LeaveType")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class AttendanceCorrection(Base, TimestampMixin):
    __tablename__ = "attendance_corrections"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    requested_check_in = Column(DateTime, nullable=True)
    requested_check_out = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="attendance_corrections")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_payroll_year_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    status = Column(Enum(PayrollStatus), default=PayrollStatus.DRAFT, nullable=False)
    total_payout = Column(Numeric(14, 2), default=0.00, nullable=False)
    finalized_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    finalizer = relationship("User", foreign_keys=[finalized_by])
    payslips = relationship("Payslip", back_populates="payroll_run", cascade="all, delete-orphan")


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_payslip_run_emp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    working_days_in_month = Column(Integer, nullable=False)
    worked_days = Column(Float, nullable=False)
    basic_salary = Column(Numeric(12, 2), nullable=False)
    gross_salary = Column(Numeric(12, 2), nullable=False)
    daily_rate = Column(Numeric(12, 2), nullable=False)
    absent_days = Column(Float, default=0.0, nullable=False)
    unpaid_leave_days = Column(Float, default=0.0, nullable=False)
    half_days = Column(Integer, default=0, nullable=False)
    deductions = Column(Numeric(12, 2), default=0.00, nullable=False)
    annual_gross = Column(Numeric(14, 2), nullable=False)
    annual_tax = Column(Numeric(14, 2), default=0.00, nullable=False)
    monthly_tax = Column(Numeric(12, 2), default=0.00, nullable=False)
    net_salary = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    payroll_run = relationship("PayrollRun", back_populates="payslips")
    employee = relationship("Employee", back_populates="payslips")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    author = relationship("User", foreign_keys=[created_by])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, APPROVE, FINALIZE, SETUP, etc.
    entity = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=True)
    before_state = Column(Text, nullable=True)  # JSON string
    after_state = Column(Text, nullable=True)   # JSON string
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    actor = relationship("User", foreign_keys=[actor_id])


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)   # JSON string
    response = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
