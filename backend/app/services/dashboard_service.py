from datetime import date, datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.models import (
    User, UserRole, Employee, Department, Designation, Attendance,
    AttendanceStatus, LeaveRequest, LeaveBalance, LeaveType, ApprovalStatus,
    AttendanceCorrection, PayrollRun, PayrollStatus, Payslip, AuditLog,
    Announcement
)
from app.schemas.dashboard import (
    HRDashboardResponse, AdminDashboardResponse, EmployeeDashboardResponse
)
from app.services.attendance_service import AttendanceService
from app.services.org_service import OrgService


class DashboardService:
    @staticmethod
    def get_hr_dashboard(
        db: Session,
        current_user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        department_id: Optional[int] = None
    ) -> HRDashboardResponse:
        if current_user.role not in (UserRole.HR, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only HR personnel and Administrators can view the HR dashboard."
            )

        today = date.today()
        if not start_date:
            start_date = today - timedelta(days=14)
        if not end_date:
            end_date = today

        # 1. Base Employee Query
        emp_query = db.query(Employee).join(User, Employee.user_id == User.id).filter(User.is_active == True)
        if department_id:
            emp_query = emp_query.filter(Employee.department_id == department_id)
        active_employees = emp_query.all()
        headcount = len(active_employees)
        emp_ids = [e.id for e in active_employees]

        # 2. Today's Attendance Snapshot
        today_att_query = db.query(Attendance).filter(Attendance.date == today)
        if emp_ids:
            today_att_query = today_att_query.filter(Attendance.employee_id.in_(emp_ids))
        today_attendances = today_att_query.all() if emp_ids else []

        present_today = sum(1 for a in today_attendances if a.status in (AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY))
        late_today = sum(1 for a in today_attendances if a.status == AttendanceStatus.LATE)
        on_leave_today = sum(1 for a in today_attendances if a.status == AttendanceStatus.ON_LEAVE)

        # Also check approved leaves covering today
        leave_today_query = db.query(LeaveRequest).filter(
            LeaveRequest.status == ApprovalStatus.APPROVED,
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today
        )
        if emp_ids:
            leave_today_query = leave_today_query.filter(LeaveRequest.employee_id.in_(emp_ids))
        leaves_today_count = leave_today_query.count() if emp_ids else 0
        on_leave_today = max(on_leave_today, leaves_today_count)

        # 3. Pending Approvals
        pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == ApprovalStatus.PENDING)
        pending_corrections = db.query(AttendanceCorrection).filter(AttendanceCorrection.status == ApprovalStatus.PENDING)
        if emp_ids:
            pending_leaves = pending_leaves.filter(LeaveRequest.employee_id.in_(emp_ids))
            pending_corrections = pending_corrections.filter(AttendanceCorrection.employee_id.in_(emp_ids))
        pending_approvals = (pending_leaves.count() if emp_ids else 0) + (pending_corrections.count() if emp_ids else 0)

        # 4. Period Attendance and Rates
        range_att_query = db.query(Attendance).filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        if emp_ids:
            range_att_query = range_att_query.filter(Attendance.employee_id.in_(emp_ids))
        range_atts = range_att_query.all() if emp_ids else []

        present_cnt = sum(1 for a in range_atts if a.status == AttendanceStatus.PRESENT)
        late_cnt = sum(1 for a in range_atts if a.status == AttendanceStatus.LATE)
        half_day_cnt = sum(1 for a in range_atts if a.status == AttendanceStatus.HALF_DAY)
        missing_cnt = sum(1 for a in range_atts if a.status == AttendanceStatus.MISSING_CHECKOUT)
        on_leave_cnt = sum(1 for a in range_atts if a.status == AttendanceStatus.ON_LEAVE)

        total_records = len(range_atts)
        effective_base = total_records - on_leave_cnt
        if effective_base > 0:
            attendance_rate = round(((present_cnt + late_cnt + missing_cnt + (0.5 * half_day_cnt)) / effective_base) * 100.0, 2)
        else:
            attendance_rate = 100.0 if total_records > 0 else 0.0

        if (present_cnt + late_cnt) > 0:
            late_percentage = round((late_cnt / (present_cnt + late_cnt)) * 100.0, 2)
        else:
            late_percentage = 0.0

        # 5. Attendance Trend (daily over the range, capped at last 14 days)
        trend_days = []
        cur = max(start_date, end_date - timedelta(days=13))
        att_by_date = {}
        for a in range_atts:
            att_by_date.setdefault(a.date, []).append(a)

        while cur <= end_date:
            day_atts = att_by_date.get(cur, [])
            trend_days.append({
                "date": str(cur),
                "present": sum(1 for a in day_atts if a.status in (AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY)),
                "late": sum(1 for a in day_atts if a.status == AttendanceStatus.LATE),
                "on_leave": sum(1 for a in day_atts if a.status == AttendanceStatus.ON_LEAVE)
            })
            cur = date.fromordinal(cur.toordinal() + 1)

        # 6. Absenteeism by Department
        departments = db.query(Department).all()
        absenteeism_by_dept = []
        for d in departments:
            d_emps = [e for e in active_employees if e.department_id == d.id]
            if not d_emps:
                continue
            # Calculate working days in range
            d_count = len(d_emps)
            expected_work_days = max(1, d_count * 10)  # Approximation for 2 weeks
            # Attendances recorded for this dept in range
            dept_att_count = sum(1 for a in range_atts if a.employee and a.employee.department_id == d.id and a.status != AttendanceStatus.ON_LEAVE)
            absent_estimated = max(0, expected_work_days - dept_att_count)
            rate = round((absent_estimated / expected_work_days) * 100.0, 2)
            absenteeism_by_dept.append({
                "department_name": d.name,
                "absent_days": absent_estimated,
                "expected_days": expected_work_days,
                "absenteeism_rate": rate
            })

        # 7. Leave by Type and Utilization
        leave_types = db.query(LeaveType).all()
        leave_by_type = []
        for lt in leave_types:
            approved_days = db.query(func.coalesce(func.sum(LeaveRequest.working_days_count), 0)).filter(
                LeaveRequest.leave_type_id == lt.id,
                LeaveRequest.status == ApprovalStatus.APPROVED
            ).scalar() or 0
            quota = lt.yearly_quota * max(1, headcount)
            utilization = round((approved_days / quota) * 100.0, 2) if quota > 0 else 0.0
            leave_by_type.append({
                "leave_type": lt.name,
                "approved_days": approved_days,
                "quota": quota,
                "utilization_rate": utilization
            })

        # 8. Top 5 Late Comers
        late_group = db.query(
            Attendance.employee_id,
            func.count(Attendance.id).label("late_count")
        ).filter(
            Attendance.status == AttendanceStatus.LATE
        )
        if emp_ids:
            late_group = late_group.filter(Attendance.employee_id.in_(emp_ids))
        top_late_results = late_group.group_by(Attendance.employee_id).order_by(func.count(Attendance.id).desc()).limit(5).all()

        top_late_comers = []
        for emp_id, l_cnt in top_late_results:
            e = db.query(Employee).filter(Employee.id == emp_id).first()
            if e:
                top_late_comers.append({
                    "employee_id": e.id,
                    "employee_code": e.employee_code,
                    "employee_name": f"{e.first_name} {e.last_name}",
                    "late_count": l_cnt
                })

        return HRDashboardResponse(
            headcount=headcount,
            present_today=present_today,
            on_leave_today=on_leave_today,
            late_today=late_today,
            pending_approvals=pending_approvals,
            attendance_rate=attendance_rate,
            late_percentage=late_percentage,
            attendance_trend=trend_days,
            absenteeism_by_dept=absenteeism_by_dept,
            leave_by_type=leave_by_type,
            top_late_comers=top_late_comers
        )

    @staticmethod
    def get_admin_dashboard(db: Session, current_user: User) -> AdminDashboardResponse:
        # Rule: Admin only; HR cannot read Admin dashboard
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Admin dashboard is restricted to Administrators only."
            )

        active_employees = db.query(Employee).join(User, Employee.user_id == User.id).filter(User.is_active == True).all()
        headcount = len(active_employees)

        # Attrition YTD: exits this year / max(1, headcount) * 100
        cur_year = datetime.now(timezone.utc).year
        exits_ytd = db.query(Employee).filter(
            Employee.exit_date.isnot(None),
            func.extract("year", Employee.exit_date) == cur_year
        ).count()
        attrition_ytd = round((exits_ytd / max(1, headcount)) * 100.0, 2)

        # Payroll Cost from latest finalized run
        latest_finalized = db.query(PayrollRun).filter(PayrollRun.status == PayrollStatus.FINALIZED).order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).first()
        payroll_cost = float(latest_finalized.total_payout) if latest_finalized else sum(float(e.basic_salary) * 1.5 for e in active_employees)

        # Average Salary
        avg_salary = round(sum(float(e.basic_salary) for e in active_employees) / max(1, headcount), 2)

        # Headcount and Payroll by Department
        departments = db.query(Department).all()
        headcount_by_dept = []
        payroll_cost_by_dept = []
        for d in departments:
            d_emps = [e for e in active_employees if e.department_id == d.id]
            d_count = len(d_emps)
            d_cost = round(sum(float(e.basic_salary) * 1.5 for e in d_emps), 2)
            headcount_by_dept.append({"department_name": d.name, "count": d_count})
            payroll_cost_by_dept.append({"department_name": d.name, "total_cost": d_cost})

        # Gender Distribution
        gender_counts = db.query(
            Employee.gender,
            func.count(Employee.id)
        ).group_by(Employee.gender).all()
        gender_distribution = [{"gender": g or "Unspecified", "count": c} for g, c in gender_counts]

        # Tenure Distribution
        today = date.today()
        tenure_brackets = {"< 1 Year": 0, "1 - 3 Years": 0, "3 - 5 Years": 0, "5+ Years": 0}
        for e in active_employees:
            years = (today - e.joining_date).days / 365.25
            if years < 1:
                tenure_brackets["< 1 Year"] += 1
            elif years < 3:
                tenure_brackets["1 - 3 Years"] += 1
            elif years < 5:
                tenure_brackets["3 - 5 Years"] += 1
            else:
                tenure_brackets["5+ Years"] += 1
        tenure_distribution = [{"bracket": k, "count": v} for k, v in tenure_brackets.items()]

        # Last 10 Audit Entries
        audit_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
        recent_audits = [
            {
                "id": a.id,
                "action": a.action,
                "entity": a.entity,
                "entity_id": a.entity_id,
                "timestamp": a.timestamp.isoformat(),
                "actor_id": a.actor_id
            }
            for a in audit_logs
        ]

        return AdminDashboardResponse(
            headcount=headcount,
            attrition_ytd=attrition_ytd,
            payroll_cost=round(payroll_cost, 2),
            average_salary=avg_salary,
            headcount_by_dept=headcount_by_dept,
            payroll_cost_by_dept=payroll_cost_by_dept,
            gender_distribution=gender_distribution,
            tenure_distribution=tenure_distribution,
            recent_audit_logs=recent_audits
        )

    @staticmethod
    def get_employee_dashboard(db: Session, current_user: User) -> EmployeeDashboardResponse:
        # Rule: Employee sees own data only
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to an employee profile."
            )

        emp = current_user.employee
        today = date.today()

        # Hours this week (Monday to Sunday)
        start_of_week = today - timedelta(days=today.weekday())
        week_atts = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_of_week,
            Attendance.date <= today
        ).all()
        hours_this_week = round(sum(a.work_hours for a in week_atts), 2)

        # Late count this month
        first_day_month = date(today.year, today.month, 1)
        late_count = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= first_day_month,
            Attendance.date <= today,
            Attendance.status == AttendanceStatus.LATE
        ).count()

        # Leave Balances
        leave_balances = []
        for lb in emp.leave_balances:
            rem = max(0.0, float(lb.leave_type.yearly_quota) - float(lb.used_days))
            leave_balances.append({
                "leave_type": lb.leave_type.name,
                "quota": lb.leave_type.yearly_quota,
                "used": float(lb.used_days),
                "remaining": rem
            })

        # Last Payslip
        latest_payslip = db.query(Payslip).join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id).filter(
            Payslip.employee_id == emp.id,
            PayrollRun.status == PayrollStatus.FINALIZED
        ).order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).first()

        last_payslip_dict = None
        if latest_payslip:
            last_payslip_dict = {
                "payslip_id": latest_payslip.id,
                "year": latest_payslip.payroll_run.year,
                "month": latest_payslip.payroll_run.month,
                "net_salary": float(latest_payslip.net_salary),
                "gross_salary": float(latest_payslip.gross_salary)
            }

        # Recent Announcements (last 5)
        announcements = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(5).all()
        recent_ann = [
            {
                "id": ann.id,
                "title": ann.title,
                "body": ann.body,
                "created_at": ann.created_at.isoformat(),
                "author": ann.author.email if ann.author else "HR"
            }
            for ann in announcements
        ]

        return EmployeeDashboardResponse(
            employee_id=emp.id,
            employee_name=f"{emp.first_name} {emp.last_name}",
            hours_this_week=hours_this_week,
            standard_weekly_hours=40.0,
            late_count_this_month=late_count,
            leave_balances=leave_balances,
            last_payslip=last_payslip_dict,
            recent_announcements=recent_ann
        )
