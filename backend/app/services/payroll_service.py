import calendar
import io
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.models.models import (
    User, UserRole, Employee, Attendance, AttendanceStatus,
    LeaveRequest, ApprovalStatus, PayrollRun, PayrollStatus,
    Payslip, Holiday, Notification
)
from app.schemas.payroll import (
    PayrollCreateDraftRequest, PayrollRunResponse, PayslipResponse
)
from app.services.audit_service import AuditService
from app.services.org_service import OrgService


class PayrollService:
    @staticmethod
    def _parse_weekend_days(weekend_str: str) -> list[int]:
        try:
            return [int(x.strip()) for x in weekend_str.split(",") if x.strip().isdigit()]
        except Exception:
            return [5, 6]

    @staticmethod
    def calculate_annual_tax(annual_gross: float) -> float:
        """
        Tax slab on gross x 12:
        - 0 to 600k: 0
        - >600k to 1.2M: 5% of excess over 600k
        - >1.2M to 2.4M: 30k + 15% of excess over 1.2M
        - >2.4M to 3.6M: 210k + 25% of excess over 2.4M
        - >3.6M: 510k + 35% of excess over 3.6M
        """
        if annual_gross <= 600000.0:
            return 0.0
        elif annual_gross <= 1200000.0:
            return (annual_gross - 600000.0) * 0.05
        elif annual_gross <= 2400000.0:
            return 30000.0 + (annual_gross - 1200000.0) * 0.15
        elif annual_gross <= 3600000.0:
            return 210000.0 + (annual_gross - 2400000.0) * 0.25
        else:
            return 510000.0 + (annual_gross - 3600000.0) * 0.35

    @staticmethod
    def get_working_days_in_month(db: Session, year: int, month: int) -> list[date]:
        settings = OrgService.get_settings(db)
        weekend_days = PayrollService._parse_weekend_days(settings.weekend_days)
        _, num_days = calendar.monthrange(year, month)

        holidays = db.query(Holiday.date).filter(
            Holiday.date >= date(year, month, 1),
            Holiday.date <= date(year, month, num_days)
        ).all()
        holiday_dates = {h[0] for h in holidays}

        working_dates = []
        for day in range(1, num_days + 1):
            cur = date(year, month, day)
            if cur.weekday() not in weekend_days and cur not in holiday_dates:
                working_dates.append(cur)
        return working_dates

    @staticmethod
    def create_monthly_draft(
        db: Session,
        actor: User,
        data: PayrollCreateDraftRequest,
        ip_address: Optional[str] = None
    ) -> PayrollRunResponse:
        # Rule: HR creates monthly draft run (Admin view only or HR permitted)
        if actor.role != UserRole.HR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only HR personnel can generate payroll draft runs."
            )

        year, month = data.year, data.month
        _, num_days = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, num_days)

        # Check existing run
        existing_run = db.query(PayrollRun).filter(
            PayrollRun.year == year,
            PayrollRun.month == month
        ).first()

        if existing_run and existing_run.status == PayrollStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payroll run for this month is already FINALIZED and locked."
            )

        month_working_dates = PayrollService.get_working_days_in_month(db, year, month)
        total_working_days = len(month_working_dates)
        if total_working_days == 0:
            total_working_days = 1  # Avoid division by zero

        payroll_run = existing_run
        if not payroll_run:
            payroll_run = PayrollRun(
                year=year,
                month=month,
                status=PayrollStatus.DRAFT,
                total_payout=0.0
            )
            db.add(payroll_run)
            db.flush()
        else:
            # Delete existing draft payslips to recompute
            db.query(Payslip).filter(Payslip.payroll_run_id == payroll_run.id).delete()

        # Query all employees active in this month
        employees = db.query(Employee).filter(
            Employee.joining_date <= month_end,
            (Employee.exit_date.is_(None) | (Employee.exit_date >= month_start))
        ).all()

        total_net_payout = 0.0
        payslips_created = []

        for emp in employees:
            basic = float(emp.basic_salary)
            gross = round(basic * 1.5, 2)
            daily_rate = round(gross / total_working_days, 2)

            # Query attendance records in month
            attendances = db.query(Attendance).filter(
                Attendance.employee_id == emp.id,
                Attendance.date >= month_start,
                Attendance.date <= month_end
            ).all()
            att_map = {a.date: a for a in attendances}

            # Query unpaid leaves in month
            unpaid_leaves = db.query(LeaveRequest).join(LeaveRequest.leave_type).filter(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.status == ApprovalStatus.APPROVED,
                LeaveRequest.start_date <= month_end,
                LeaveRequest.end_date >= month_start,
                (LeaveRequest.leave_type.has(name="UNPAID") | (LeaveRequest.leave_type.has(is_paid=False)))
            ).all()

            unpaid_leave_dates = set()
            for ulv in unpaid_leaves:
                c = max(ulv.start_date, month_start)
                end_c = min(ulv.end_date, month_end)
                while c <= end_c:
                    if c in month_working_dates:
                        unpaid_leave_dates.add(c)
                    c = date.fromordinal(c.toordinal() + 1)

            # Query all approved leaves (paid or unpaid)
            all_approved_leaves = db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.status == ApprovalStatus.APPROVED,
                LeaveRequest.start_date <= month_end,
                LeaveRequest.end_date >= month_start
            ).all()
            approved_leave_dates = set()
            for alv in all_approved_leaves:
                c = max(alv.start_date, month_start)
                end_c = min(alv.end_date, month_end)
                while c <= end_c:
                    if c in month_working_dates:
                        approved_leave_dates.add(c)
                    c = date.fromordinal(c.toordinal() + 1)

            # Calculate deductions
            absent_count = 0
            half_day_count = 0
            late_count = 0
            prorate_unworked_count = 0

            for w_date in month_working_dates:
                # Prorating: check if joined after or exited before this date
                if w_date < emp.joining_date or (emp.exit_date and w_date > emp.exit_date):
                    prorate_unworked_count += 1
                elif w_date in att_map:
                    att = att_map[w_date]
                    if att.status == AttendanceStatus.HALF_DAY:
                        half_day_count += 1
                    elif att.status == AttendanceStatus.LATE:
                        late_count += 1
                elif w_date in approved_leave_dates:
                    pass  # Approved leave is accounted for
                else:
                    # Absent on working day
                    absent_count += 1

            unpaid_days_count = len(unpaid_leave_dates)

            # Bonus rule: 3 lates = 0.5 day deduction
            late_penalty_days = (late_count // 3) * 0.5

            # Rule: deduct absent + unpaid + 0.5 x half days + late penalty; prorate joiners/leavers
            total_deduct_days = (
                float(absent_count)
                + float(unpaid_days_count)
                + (0.5 * float(half_day_count))
                + float(prorate_unworked_count)
                + float(late_penalty_days)
            )
            deductions = round(total_deduct_days * daily_rate, 2)

            annual_gross = round(gross * 12.0, 2)
            annual_tax = round(PayrollService.calculate_annual_tax(annual_gross), 2)
            monthly_tax = round(annual_tax / 12.0, 2)

            net_salary = round(max(0.0, gross - deductions - monthly_tax), 2)
            worked_days = max(0.0, float(total_working_days) - total_deduct_days)

            payslip = Payslip(
                payroll_run_id=payroll_run.id,
                employee_id=emp.id,
                working_days_in_month=total_working_days,
                worked_days=worked_days,
                basic_salary=basic,
                gross_salary=gross,
                daily_rate=daily_rate,
                absent_days=float(absent_count + prorate_unworked_count),
                unpaid_leave_days=float(unpaid_days_count),
                half_days=half_day_count,
                deductions=deductions,
                annual_gross=annual_gross,
                annual_tax=annual_tax,
                monthly_tax=monthly_tax,
                net_salary=net_salary
            )
            db.add(payslip)
            payslips_created.append(payslip)
            total_net_payout += net_salary

        payroll_run.total_payout = total_net_payout
        db.commit()
        db.refresh(payroll_run)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_PAYROLL_DRAFT",
            entity="PayrollRun",
            entity_id=payroll_run.id,
            after={
                "year": year,
                "month": month,
                "status": "DRAFT",
                "employee_count": len(payslips_created),
                "total_payout": total_net_payout
            },
            ip_address=ip_address
        )

        return PayrollService.get_payroll_run(db, actor, payroll_run.id)

    @staticmethod
    def get_payroll_run(db: Session, current_user: User, run_id: int) -> PayrollRunResponse:
        run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found.")

        payslips_query = db.query(Payslip).filter(Payslip.payroll_run_id == run.id)
        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee:
                payslips_query = payslips_query.filter(Payslip.id == -1)
            else:
                payslips_query = payslips_query.filter(Payslip.employee_id == current_user.employee.id)

        payslip_rows = payslips_query.all()
        payslip_responses = [
            PayslipResponse(
                id=p.id,
                payroll_run_id=p.payroll_run_id,
                employee_id=p.employee_id,
                employee_code=p.employee.employee_code,
                employee_name=f"{p.employee.first_name} {p.employee.last_name}",
                department_name=p.employee.department.name if p.employee.department else "",
                working_days_in_month=p.working_days_in_month,
                worked_days=p.worked_days,
                basic_salary=float(p.basic_salary),
                hra=round(float(p.basic_salary) * 0.40, 2),
                medical_allowance=round(float(p.basic_salary) * 0.10, 2),
                gross_salary=float(p.gross_salary),
                daily_rate=float(p.daily_rate),
                absent_days=float(p.absent_days),
                unpaid_leave_days=float(p.unpaid_leave_days),
                half_days=p.half_days,
                deductions=float(p.deductions),
                annual_gross=float(p.annual_gross),
                annual_tax=float(p.annual_tax),
                monthly_tax=float(p.monthly_tax),
                net_salary=float(p.net_salary),
                created_at=p.created_at
            )
            for p in payslip_rows
        ]

        return PayrollRunResponse(
            id=run.id,
            year=run.year,
            month=run.month,
            status=run.status.value,
            total_payout=float(run.total_payout),
            finalized_by=run.finalized_by,
            finalized_at=run.finalized_at,
            created_at=run.created_at,
            payslip_count=len(run.payslips),
            payslips=payslip_responses
        )

    @staticmethod
    def list_payroll_runs(db: Session, current_user: User) -> list[PayrollRunResponse]:
        runs = db.query(PayrollRun).order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).all()
        return [
            PayrollRunResponse(
                id=r.id,
                year=r.year,
                month=r.month,
                status=r.status.value,
                total_payout=float(r.total_payout),
                finalized_by=r.finalized_by,
                finalized_at=r.finalized_at,
                created_at=r.created_at,
                payslip_count=len(r.payslips),
                payslips=None
            )
            for r in runs
        ]

    @staticmethod
    def finalize_payroll(
        db: Session,
        actor: User,
        run_id: int,
        ip_address: Optional[str] = None
    ) -> PayrollRunResponse:
        # Rule: Only Admin can FINALIZE; finalized runs are locked. HR cannot finalize.
        if actor.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only Administrators can finalize payroll runs. HR is not authorized."
            )

        run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found.")

        if run.status == PayrollStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This payroll run is already FINALIZED and locked against further changes."
            )

        run.status = PayrollStatus.FINALIZED
        run.finalized_by = actor.id
        run.finalized_at = datetime.now(timezone.utc)

        # Rule: Notify on finalize
        for p in run.payslips:
            emp = p.employee
            if emp and emp.user_id:
                notif = Notification(
                    user_id=emp.user_id,
                    message=f"Payroll for {run.month:02d}/{run.year} has been finalized. Your net payable salary is PKR {float(p.net_salary):,.2f}."
                )
                db.add(notif)

        db.commit()
        db.refresh(run)

        AuditService.log(
            db=db,
            actor=actor,
            action="FINALIZE_PAYROLL",
            entity="PayrollRun",
            entity_id=run.id,
            after={"year": run.year, "month": run.month, "status": "FINALIZED", "total_payout": float(run.total_payout)},
            ip_address=ip_address
        )
        return PayrollService.get_payroll_run(db, actor, run.id)

    @staticmethod
    def generate_payslip_pdf(
        db: Session,
        current_user: User,
        payslip_id: int
    ) -> tuple[bytes, str]:
        payslip = db.query(Payslip).filter(Payslip.id == payslip_id).first()
        if not payslip:
            raise HTTPException(status_code=404, detail="Payslip not found.")

        # Rule: Employee downloads only own payslip
        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee or current_user.employee.id != payslip.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are only permitted to download your own payslip."
                )

        emp = payslip.employee
        run = payslip.payroll_run
        settings = OrgService.get_settings(db)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e293b"),
            alignment=1
        )
        subtitle_style = ParagraphStyle(
            name="SubTitleStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            alignment=1
        )

        elements.append(Paragraph(f"<b>{settings.company_name}</b>", title_style))
        elements.append(Paragraph(f"PAYSLIP FOR {calendar.month_name[run.month].upper()} {run.year}", subtitle_style))
        elements.append(Spacer(1, 15))

        # Employee metadata table
        emp_data = [
            ["Employee Code:", emp.employee_code, "Designation:", emp.designation.name if emp.designation else "N/A"],
            ["Employee Name:", f"{emp.first_name} {emp.last_name}", "Department:", emp.department.name if emp.department else "N/A"],
            ["Working Days in Month:", str(payslip.working_days_in_month), "Worked Days:", str(payslip.worked_days)],
            ["Daily Rate:", f"PKR {float(payslip.daily_rate):,.2f}", "Status:", run.status.value],
        ]
        emp_table = Table(emp_data, colWidths=[130, 140, 130, 140])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#334155")),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        elements.append(emp_table)
        elements.append(Spacer(1, 15))

        # Financials Table
        basic = float(payslip.basic_salary)
        hra = round(basic * 0.40, 2)
        med = round(basic * 0.10, 2)
        gross = float(payslip.gross_salary)

        fin_data = [
            ["EARNINGS", "AMOUNT (PKR)", "DEDUCTIONS", "AMOUNT (PKR)"],
            ["Basic Salary", f"{basic:,.2f}", f"Absent / Prorate Days ({payslip.absent_days})", f"{float(payslip.deductions):,.2f}"],
            ["House Rent Allowance (HRA 40%)", f"{hra:,.2f}", "Income Tax Deduction", f"{float(payslip.monthly_tax):,.2f}"],
            ["Medical Allowance (10%)", f"{med:,.2f}", f"Unpaid Leave Days ({payslip.unpaid_leave_days})", "Included in deductions"],
            ["", "", f"Half Days Count ({payslip.half_days})", "Included in deductions"],
            ["TOTAL GROSS SALARY", f"{gross:,.2f}", "TOTAL DEDUCTIONS", f"{(float(payslip.deductions) + float(payslip.monthly_tax)):,.2f}"],
        ]
        fin_table = Table(fin_data, colWidths=[170, 100, 170, 100])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#0284c7")),
            ('BACKGROUND', (2, 0), (3, 0), colors.HexColor("#dc2626")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, -1), (1, -1), colors.HexColor("#e0f2fe")),
            ('BACKGROUND', (2, -1), (3, -1), colors.HexColor("#fee2e2")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        elements.append(fin_table)
        elements.append(Spacer(1, 15))

        # Net Pay Block
        net_data = [
            ["NET PAYABLE AMOUNT:", f"PKR {float(payslip.net_salary):,.2f}"]
        ]
        net_table = Table(net_data, colWidths=[300, 240])
        net_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(net_table)
        elements.append(Spacer(1, 25))

        footer_text = Paragraph(
            "<i>This is a computer-generated document from HCM Lite and does not require a physical signature.</i>",
            subtitle_style
        )
        elements.append(footer_text)

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        filename = f"payslip_{emp.employee_code}_{run.year}_{run.month:02d}.pdf"
        return pdf_bytes, filename
