import math
import calendar
from datetime import date, datetime, time, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import (
    User, UserRole, Employee, Attendance, AttendanceStatus,
    CompanySettings, Holiday, LeaveRequest, ApprovalStatus,
    AttendanceCorrection, Notification
)
from app.schemas.attendance import (
    CheckInRequest, CheckOutRequest, DailyCalendarItem, MonthlyCalendarResponse,
    DailyBoardItem, DailyBoardResponse, CorrectionCreate, CorrectionReview
)
from app.services.audit_service import AuditService
from app.services.org_service import OrgService


class AttendanceService:
    @staticmethod
    def _parse_weekend_days(weekend_str: str) -> list[int]:
        try:
            return [int(x.strip()) for x in weekend_str.split(",") if x.strip().isdigit()]
        except Exception:
            return [5, 6]

    @staticmethod
    def check_in(
        db: Session,
        current_user: User,
        data: CheckInRequest,
        ip_address: Optional[str] = None
    ) -> Attendance:
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to an employee profile."
            )

        emp = current_user.employee
        now_dt = datetime.now(timezone.utc)
        today_date = now_dt.date()

        # Rule: Second check-in on same day = 409 Conflict
        existing = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date == today_date
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance check-in has already been recorded for today."
            )

        # Rule: Late if after start + grace
        settings = OrgService.get_settings(db)

        # Camera & Geofence Validation (PDF Section 5)
        if data.check_in_method == "FACE_DETECTION":
            if data.faces_detected is not None and data.faces_detected != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Camera check-in rejected: exactly one face must be detected in frame (found {data.faces_detected})."
                )
            if data.accuracy is not None and data.accuracy > 100.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Camera check-in rejected: GPS accuracy is too low ({data.accuracy:.1f}m > 100m)."
                )
            if (
                data.latitude is not None and data.longitude is not None
                and settings.office_latitude not in (None, 0.0)
                and settings.office_longitude not in (None, 0.0)
            ):
                # Haversine distance in meters
                lat1, lon1 = math.radians(data.latitude), math.radians(data.longitude)
                lat2, lon2 = math.radians(settings.office_latitude), math.radians(settings.office_longitude)
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
                c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
                dist = 6371000.0 * c
                allowed_radius = settings.office_radius_meters or 150.0
                if dist > allowed_radius:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Camera check-in rejected: Outside office area. Distance is {dist:.1f}m, allowed radius is {allowed_radius:.0f}m."
                    )
        try:
            start_parts = settings.office_start_time.split(":")
            start_h, start_m = int(start_parts[0]), int(start_parts[1])
        except Exception:
            start_h, start_m = 9, 0

        cutoff_minutes = (start_h * 60 + start_m) + settings.grace_period_minutes
        now_minutes = now_dt.hour * 60 + now_dt.minute

        att_status = AttendanceStatus.LATE if now_minutes > cutoff_minutes else AttendanceStatus.PRESENT

        attendance = Attendance(
            employee_id=emp.id,
            date=today_date,
            check_in_time=now_dt,
            check_in_lat=data.latitude,
            check_in_lng=data.longitude,
            status=att_status,
            work_hours=0.0,
            check_in_method=data.check_in_method or "NORMAL"
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)

        AuditService.log(
            db=db,
            actor=current_user,
            action="CHECK_IN",
            entity="Attendance",
            entity_id=attendance.id,
            after={
                "employee_code": emp.employee_code,
                "date": str(today_date),
                "check_in_time": str(now_dt),
                "status": att_status.value
            },
            ip_address=ip_address
        )
        return attendance

    @staticmethod
    def check_out(
        db: Session,
        current_user: User,
        data: CheckOutRequest,
        ip_address: Optional[str] = None
    ) -> Attendance:
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to an employee profile."
            )

        emp = current_user.employee
        now_dt = datetime.now(timezone.utc)
        today_date = now_dt.date()

        attendance = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date == today_date
        ).first()

        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No check-in record found for today. You must check in first."
            )

        if attendance.check_out_time is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-out has already been recorded for today."
            )

        attendance.check_out_time = now_dt
        attendance.check_out_lat = data.latitude
        attendance.check_out_lng = data.longitude

        # Compute work hours
        check_in_tz = attendance.check_in_time
        if check_in_tz.tzinfo is None:
            check_in_tz = check_in_tz.replace(tzinfo=timezone.utc)

        duration_sec = (now_dt - check_in_tz).total_seconds()
        work_hours = round(max(0.0, duration_sec / 3600.0), 2)
        attendance.work_hours = work_hours

        # Rule: half_day if under the threshold hours
        settings = OrgService.get_settings(db)
        if work_hours < settings.half_day_hours_threshold:
            attendance.status = AttendanceStatus.HALF_DAY

        db.commit()
        db.refresh(attendance)

        AuditService.log(
            db=db,
            actor=current_user,
            action="CHECK_OUT",
            entity="Attendance",
            entity_id=attendance.id,
            after={
                "employee_code": emp.employee_code,
                "date": str(today_date),
                "check_out_time": str(now_dt),
                "work_hours": work_hours,
                "status": attendance.status.value
            },
            ip_address=ip_address
        )
        return attendance

    @staticmethod
    def get_monthly_calendar(
        db: Session,
        current_user: User,
        employee_id: int,
        year: int,
        month: int
    ) -> MonthlyCalendarResponse:
        # Rule: Employee can only read their own attendance calendar
        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee or current_user.employee.id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view your own attendance calendar."
                )

        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found.")

        settings = OrgService.get_settings(db)
        weekend_days = AttendanceService._parse_weekend_days(settings.weekend_days)

        _, num_days = calendar.monthrange(year, month)
        start_month_date = date(year, month, 1)
        end_month_date = date(year, month, num_days)

        # 1. Holidays in month
        holidays = db.query(Holiday).filter(
            Holiday.date >= start_month_date,
            Holiday.date <= end_month_date
        ).all()
        holiday_map = {h.date: h.name for h in holidays}

        # 2. Approved leaves overlapping month
        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status == ApprovalStatus.APPROVED,
            LeaveRequest.start_date <= end_month_date,
            LeaveRequest.end_date >= start_month_date
        ).all()

        leave_dates = set()
        for lv in leaves:
            cur = max(lv.start_date, start_month_date)
            end_cur = min(lv.end_date, end_month_date)
            while cur <= end_cur:
                leave_dates.add(cur)
                cur = date.fromordinal(cur.toordinal() + 1)

        # 3. Attendance records in month
        attendances = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_month_date,
            Attendance.date <= end_month_date
        ).all()
        att_map = {a.date: a for a in attendances}

        today_date = datetime.now(timezone.utc).date()

        days_list: list[DailyCalendarItem] = []
        working_days = 0
        present_count = 0
        late_count = 0
        half_day_count = 0
        absent_count = 0
        on_leave_count = 0

        for day in range(1, num_days + 1):
            cur_date = date(year, month, day)
            day_name = cur_date.strftime("%A")
            is_weekend = cur_date.weekday() in weekend_days
            is_holiday = cur_date in holiday_map

            check_in_time = None
            check_out_time = None
            work_hours = 0.0
            note = None

            if cur_date > today_date:
                status_str = "UPCOMING"
            elif cur_date < emp.joining_date or (emp.exit_date and cur_date > emp.exit_date):
                status_str = "NOT_EMPLOYED"
            elif cur_date in att_map:
                att = att_map[cur_date]
                check_in_time = att.check_in_time
                check_out_time = att.check_out_time
                work_hours = att.work_hours

                # Check if missing checkout from earlier date
                if cur_date < today_date and att.status != AttendanceStatus.ON_LEAVE and att.check_out_time is None:
                    status_str = "MISSING_CHECKOUT"
                else:
                    status_str = att.status.value

                working_days += 1
                if status_str == "PRESENT":
                    present_count += 1
                elif status_str == "LATE":
                    late_count += 1
                elif status_str == "HALF_DAY":
                    half_day_count += 1
                elif status_str == "ON_LEAVE":
                    on_leave_count += 1
            else:
                # No attendance record
                if is_weekend:
                    status_str = "WEEKEND"
                elif is_holiday:
                    status_str = "HOLIDAY"
                    note = holiday_map[cur_date]
                elif cur_date in leave_dates:
                    status_str = "ON_LEAVE"
                    on_leave_count += 1
                    working_days += 1
                else:
                    # Rule: ABSENT is calculated, not stored: working day, no record, no approved leave
                    status_str = "ABSENT"
                    absent_count += 1
                    working_days += 1

            days_list.append(
                DailyCalendarItem(
                    date=cur_date,
                    day_name=day_name,
                    status=status_str,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    work_hours=work_hours,
                    note=note
                )
            )

        return MonthlyCalendarResponse(
            employee_id=emp.id,
            employee_name=f"{emp.first_name} {emp.last_name}",
            year=year,
            month=month,
            working_days=working_days,
            present_count=present_count,
            late_count=late_count,
            half_day_count=half_day_count,
            absent_count=absent_count,
            on_leave_count=on_leave_count,
            days=days_list
        )

    @staticmethod
    def get_daily_board(
        db: Session,
        current_user: User,
        target_date: date
    ) -> DailyBoardResponse:
        # Rule: Daily attendance board for HR / Admin only
        if current_user.role not in (UserRole.ADMIN, UserRole.HR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Daily attendance board is restricted to HR and Administrators."
            )

        settings = OrgService.get_settings(db)
        weekend_days = AttendanceService._parse_weekend_days(settings.weekend_days)
        is_weekend = target_date.weekday() in weekend_days

        holiday = db.query(Holiday).filter(Holiday.date == target_date).first()
        is_holiday = holiday is not None

        # Active employees on target date
        active_employees = db.query(Employee).join(User, Employee.user_id == User.id).filter(
            User.is_active == True,
            Employee.joining_date <= target_date
        ).all()

        # Attendances on target date
        attendances = db.query(Attendance).filter(Attendance.date == target_date).all()
        att_map = {a.employee_id: a for a in attendances}

        # Approved leaves covering target date
        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.status == ApprovalStatus.APPROVED,
            LeaveRequest.start_date <= target_date,
            LeaveRequest.end_date >= target_date
        ).all()
        on_leave_emp_ids = {lv.employee_id for lv in leaves}

        today_date = datetime.now(timezone.utc).date()

        roster: list[DailyBoardItem] = []
        present_cnt = 0
        late_cnt = 0
        half_day_cnt = 0
        on_leave_cnt = 0
        absent_cnt = 0
        missing_checkout_cnt = 0

        for emp in active_employees:
            if emp.exit_date and target_date > emp.exit_date:
                continue

            check_in_time = None
            check_out_time = None
            work_hours = 0.0

            if emp.id in att_map:
                att = att_map[emp.id]
                check_in_time = att.check_in_time
                check_out_time = att.check_out_time
                work_hours = att.work_hours

                if target_date < today_date and att.status != AttendanceStatus.ON_LEAVE and att.check_out_time is None:
                    status_str = "MISSING_CHECKOUT"
                    missing_checkout_cnt += 1
                else:
                    status_str = att.status.value
                    if status_str == "PRESENT":
                        present_cnt += 1
                    elif status_str == "LATE":
                        late_cnt += 1
                    elif status_str == "HALF_DAY":
                        half_day_cnt += 1
                    elif status_str == "ON_LEAVE":
                        on_leave_cnt += 1
            else:
                if is_weekend:
                    status_str = "WEEKEND"
                elif is_holiday:
                    status_str = "HOLIDAY"
                elif emp.id in on_leave_emp_ids:
                    status_str = "ON_LEAVE"
                    on_leave_cnt += 1
                else:
                    status_str = "ABSENT" if target_date <= today_date else "UPCOMING"
                    if status_str == "ABSENT":
                        absent_cnt += 1

            roster.append(
                DailyBoardItem(
                    employee_id=emp.id,
                    employee_code=emp.employee_code,
                    employee_name=f"{emp.first_name} {emp.last_name}",
                    department_name=emp.department.name if emp.department else "",
                    designation_name=emp.designation.name if emp.designation else "",
                    status=status_str,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    work_hours=work_hours
                )
            )

        return DailyBoardResponse(
            date=target_date,
            total_employees=len(roster),
            present=present_cnt,
            late=late_cnt,
            half_day=half_day_cnt,
            on_leave=on_leave_cnt,
            absent=absent_cnt,
            missing_checkout=missing_checkout_cnt,
            roster=roster
        )

    # --- Attendance Corrections ---
    @staticmethod
    def request_correction(
        db: Session,
        current_user: User,
        data: CorrectionCreate,
        ip_address: Optional[str] = None
    ) -> AttendanceCorrection:
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to an employee profile."
            )

        correction = AttendanceCorrection(
            employee_id=current_user.employee.id,
            date=data.date,
            requested_check_in=data.requested_check_in,
            requested_check_out=data.requested_check_out,
            reason=data.reason.strip(),
            status=ApprovalStatus.PENDING
        )
        db.add(correction)
        db.commit()
        db.refresh(correction)

        AuditService.log(
            db=db,
            actor=current_user,
            action="REQUEST_CORRECTION",
            entity="AttendanceCorrection",
            entity_id=correction.id,
            after={
                "employee_code": current_user.employee.employee_code,
                "date": str(correction.date),
                "reason": correction.reason
            },
            ip_address=ip_address
        )
        return correction

    @staticmethod
    def list_corrections(
        db: Session,
        current_user: User,
        status_filter: Optional[ApprovalStatus] = None
    ) -> list[AttendanceCorrection]:
        query = db.query(AttendanceCorrection)

        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee:
                return []
            query = query.filter(AttendanceCorrection.employee_id == current_user.employee.id)

        if status_filter:
            query = query.filter(AttendanceCorrection.status == status_filter)

        return query.order_by(AttendanceCorrection.created_at.desc()).all()

    @staticmethod
    def review_correction(
        db: Session,
        reviewer: User,
        correction_id: int,
        data: CorrectionReview,
        ip_address: Optional[str] = None
    ) -> AttendanceCorrection:
        # Rule: HR approves or rejects with a comment
        if reviewer.role != UserRole.HR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only HR personnel can approve or reject attendance corrections."
            )

        correction = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == correction_id).first()
        if not correction:
            raise HTTPException(status_code=404, detail="Attendance correction request not found.")

        if correction.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Correction request has already been reviewed ({correction.status.value})."
            )

        before_state = {"status": correction.status.value}
        correction.status = data.status
        correction.reviewed_by = reviewer.id
        correction.comment = data.comment.strip()

        # Rule: on approval update the attendance record
        if data.status == ApprovalStatus.APPROVED:
            att = db.query(Attendance).filter(
                Attendance.employee_id == correction.employee_id,
                Attendance.date == correction.date
            ).first()

            if not att:
                att = Attendance(
                    employee_id=correction.employee_id,
                    date=correction.date,
                    status=AttendanceStatus.PRESENT,
                    work_hours=0.0
                )
                db.add(att)

            if correction.requested_check_in:
                att.check_in_time = correction.requested_check_in
            if correction.requested_check_out:
                att.check_out_time = correction.requested_check_out

            # Recalculate work hours and status
            if att.check_in_time and att.check_out_time:
                ci = att.check_in_time
                if ci.tzinfo is None:
                    ci = ci.replace(tzinfo=timezone.utc)
                co = att.check_out_time
                if co.tzinfo is None:
                    co = co.replace(tzinfo=timezone.utc)
                diff = (co - ci).total_seconds()
                hours = round(max(0.0, diff / 3600.0), 2)
                att.work_hours = hours

                settings = OrgService.get_settings(db)
                if hours < settings.half_day_hours_threshold:
                    att.status = AttendanceStatus.HALF_DAY
                else:
                    try:
                        start_h, start_m = map(int, settings.office_start_time.split(":"))
                    except Exception:
                        start_h, start_m = 9, 0
                    cutoff = (start_h * 60 + start_m) + settings.grace_period_minutes
                    ci_min = ci.hour * 60 + ci.minute
                    att.status = AttendanceStatus.LATE if ci_min > cutoff else AttendanceStatus.PRESENT
            elif att.check_in_time:
                settings = OrgService.get_settings(db)
                try:
                    start_h, start_m = map(int, settings.office_start_time.split(":"))
                except Exception:
                    start_h, start_m = 9, 0
                cutoff = (start_h * 60 + start_m) + settings.grace_period_minutes
                ci = att.check_in_time
                ci_min = ci.hour * 60 + ci.minute
                att.status = AttendanceStatus.LATE if ci_min > cutoff else AttendanceStatus.PRESENT

        # Rule: create an in-app notification for the employee on every decision
        target_employee = correction.employee
        if target_employee and target_employee.user_id:
            notif = Notification(
                user_id=target_employee.user_id,
                message=(
                    f"Your attendance correction request for {correction.date} "
                    f"was {data.status.value}. HR Comment: {data.comment.strip()}"
                )
            )
            db.add(notif)

        db.commit()
        db.refresh(correction)

        AuditService.log(
            db=db,
            actor=reviewer,
            action=f"REVIEW_CORRECTION_{data.status.value}",
            entity="AttendanceCorrection",
            entity_id=correction.id,
            before=before_state,
            after={"status": data.status.value, "comment": data.comment.strip()},
            ip_address=ip_address
        )
        return correction
