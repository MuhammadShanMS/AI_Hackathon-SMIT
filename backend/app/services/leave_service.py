from datetime import date, datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import (
    User, UserRole, Employee, LeaveType, LeaveBalance, LeaveRequest,
    ApprovalStatus, Attendance, AttendanceStatus, Holiday, Notification
)
from app.schemas.leave import (
    LeaveApplyRequest, LeaveBalanceResponse, LeaveRequestResponse, LeaveReviewRequest
)
from app.services.audit_service import AuditService
from app.services.org_service import OrgService


class LeaveService:
    @staticmethod
    def _parse_weekend_days(weekend_str: str) -> list[int]:
        try:
            return [int(x.strip()) for x in weekend_str.split(",") if x.strip().isdigit()]
        except Exception:
            return [5, 6]

    @staticmethod
    def count_working_days(db: Session, start_date: date, end_date: date) -> int:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_date must be before or equal to end_date."
            )

        settings = OrgService.get_settings(db)
        weekend_days = LeaveService._parse_weekend_days(settings.weekend_days)

        holidays = db.query(Holiday.date).filter(
            Holiday.date >= start_date,
            Holiday.date <= end_date
        ).all()
        holiday_dates = {h[0] for h in holidays}

        working_days = 0
        cur = start_date
        while cur <= end_date:
            is_weekend = cur.weekday() in weekend_days
            is_holiday = cur in holiday_dates
            if not is_weekend and not is_holiday:
                working_days += 1
            cur = date.fromordinal(cur.toordinal() + 1)

        return working_days

    @staticmethod
    def apply_leave(
        db: Session,
        current_user: User,
        data: LeaveApplyRequest,
        ip_address: Optional[str] = None
    ) -> LeaveRequestResponse:
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to an employee profile."
            )

        emp = current_user.employee
        if data.start_date > data.end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Start date must be before or equal to end date."
            )

        # 1. Calculate working days (skipping weekends and holidays)
        working_days = LeaveService.count_working_days(db, data.start_date, data.end_date)
        if working_days == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected date range contains no working days (all weekends or public holidays)."
            )

        # 2. Rule: Overlap with PENDING/APPROVED leave = 422
        overlapping = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status.in_([ApprovalStatus.PENDING, ApprovalStatus.APPROVED]),
            LeaveRequest.start_date <= data.end_date,
            LeaveRequest.end_date >= data.start_date
        ).first()

        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Leave request overlaps with an existing pending or approved leave request."
            )

        # 3. Rule: Over-balance = 422 (unpaid unlimited)
        leave_type = db.query(LeaveType).filter(LeaveType.id == data.leave_type_id).first()
        if not leave_type:
            raise HTTPException(status_code=404, detail="Leave type not found.")

        is_unpaid = leave_type.name.upper() == "UNPAID" or not leave_type.is_paid

        if not is_unpaid:
            year = data.start_date.year
            balance = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == emp.id,
                LeaveBalance.leave_type_id == leave_type.id,
                LeaveBalance.year == year
            ).first()

            if not balance:
                balance = LeaveBalance(
                    employee_id=emp.id,
                    leave_type_id=leave_type.id,
                    year=year,
                    used_days=0.0
                )
                db.add(balance)
                db.flush()

            remaining = max(0.0, float(leave_type.yearly_quota) - float(balance.used_days))
            if working_days > remaining:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Insufficient leave balance for {leave_type.name}. Requested: {working_days} working days, Available: {remaining} days."
                )

        # 4. Create Leave Request
        leave_req = LeaveRequest(
            employee_id=emp.id,
            leave_type_id=data.leave_type_id,
            start_date=data.start_date,
            end_date=data.end_date,
            working_days_count=working_days,
            reason=data.reason.strip() if data.reason else None,
            status=ApprovalStatus.PENDING
        )
        db.add(leave_req)
        db.commit()
        db.refresh(leave_req)

        AuditService.log(
            db=db,
            actor=current_user,
            action="APPLY_LEAVE",
            entity="LeaveRequest",
            entity_id=leave_req.id,
            after={
                "employee_code": emp.employee_code,
                "leave_type": leave_type.name,
                "start_date": str(leave_req.start_date),
                "end_date": str(leave_req.end_date),
                "working_days": working_days
            },
            ip_address=ip_address
        )

        return LeaveRequestResponse(
            id=leave_req.id,
            employee_id=emp.id,
            employee_code=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name}",
            leave_type_id=leave_type.id,
            leave_type_name=leave_type.name,
            start_date=leave_req.start_date,
            end_date=leave_req.end_date,
            working_days_count=leave_req.working_days_count,
            reason=leave_req.reason,
            status=leave_req.status.value,
            reviewed_by=leave_req.reviewed_by,
            review_comment=leave_req.review_comment,
            created_at=leave_req.created_at
        )

    @staticmethod
    def cancel_leave(
        db: Session,
        current_user: User,
        leave_id: int,
        ip_address: Optional[str] = None
    ) -> dict:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="User account is not linked to an employee profile.")

        leave_req = db.query(LeaveRequest).filter(
            LeaveRequest.id == leave_id,
            LeaveRequest.employee_id == current_user.employee.id
        ).first()

        if not leave_req:
            raise HTTPException(status_code=404, detail="Leave request not found.")

        # Rule: can cancel while PENDING
        if leave_req.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a leave request with status '{leave_req.status.value}'. Only PENDING requests can be cancelled."
            )

        before_state = {"status": leave_req.status.value}
        leave_req.status = ApprovalStatus.CANCELLED
        db.commit()

        AuditService.log(
            db=db,
            actor=current_user,
            action="CANCEL_LEAVE",
            entity="LeaveRequest",
            entity_id=leave_req.id,
            before=before_state,
            after={"status": "CANCELLED"},
            ip_address=ip_address
        )
        return {"message": "Leave request cancelled successfully."}

    @staticmethod
    def get_balances(
        db: Session,
        current_user: User,
        employee_id: Optional[int] = None
    ) -> list[LeaveBalanceResponse]:
        # Scoping: Employee can only see own balance
        target_id = employee_id
        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee:
                return []
            target_id = current_user.employee.id
        elif not target_id:
            if current_user.employee:
                target_id = current_user.employee.id
            else:
                first_emp = db.query(Employee).first()
                target_id = first_emp.id if first_emp else None

        if not target_id:
            return []

        year = datetime.now(timezone.utc).year
        leave_types = db.query(LeaveType).all()
        results: list[LeaveBalanceResponse] = []

        for lt in leave_types:
            bal = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == target_id,
                LeaveBalance.leave_type_id == lt.id,
                LeaveBalance.year == year
            ).first()

            used = float(bal.used_days) if bal else 0.0
            quota = lt.yearly_quota
            rem = max(0.0, float(quota) - used) if lt.is_paid else 999.0

            results.append(
                LeaveBalanceResponse(
                    leave_type_id=lt.id,
                    leave_type_name=lt.name,
                    yearly_quota=quota,
                    used_days=used,
                    remaining_days=rem,
                    is_paid=lt.is_paid
                )
            )
        return results

    @staticmethod
    def list_leaves(
        db: Session,
        current_user: User,
        employee_id: Optional[int] = None,
        status_filter: Optional[ApprovalStatus] = None
    ) -> list[LeaveRequestResponse]:
        query = db.query(LeaveRequest).join(Employee, LeaveRequest.employee_id == Employee.id).join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)

        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee:
                return []
            query = query.filter(LeaveRequest.employee_id == current_user.employee.id)
        elif employee_id:
            query = query.filter(LeaveRequest.employee_id == employee_id)

        if status_filter:
            query = query.filter(LeaveRequest.status == status_filter)

        leaves = query.order_by(LeaveRequest.created_at.desc()).all()
        return [
            LeaveRequestResponse(
                id=lv.id,
                employee_id=lv.employee_id,
                employee_code=lv.employee.employee_code,
                employee_name=f"{lv.employee.first_name} {lv.employee.last_name}",
                leave_type_id=lv.leave_type_id,
                leave_type_name=lv.leave_type.name,
                start_date=lv.start_date,
                end_date=lv.end_date,
                working_days_count=lv.working_days_count,
                reason=lv.reason,
                status=lv.status.value,
                reviewed_by=lv.reviewed_by,
                review_comment=lv.review_comment,
                created_at=lv.created_at
            )
            for lv in leaves
        ]

    @staticmethod
    def review_leave(
        db: Session,
        reviewer: User,
        leave_id: int,
        data: LeaveReviewRequest,
        ip_address: Optional[str] = None
    ) -> LeaveRequestResponse:
        # Rule: HR approves/rejects with a comment; Admin view only
        if reviewer.role != UserRole.HR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only HR personnel can approve or reject leave requests. Admin has view-only access."
            )

        leave_req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
        if not leave_req:
            raise HTTPException(status_code=404, detail="Leave request not found.")

        if leave_req.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave request is already {leave_req.status.value}."
            )

        before_state = {"status": leave_req.status.value}
        leave_req.status = data.status
        leave_req.reviewed_by = reviewer.id
        leave_req.review_comment = data.comment.strip() if data.comment else None

        # Rule: On approval deduct balance and mark those days ON_LEAVE
        if data.status == ApprovalStatus.APPROVED:
            # Deduct balance if paid leave
            if leave_req.leave_type.is_paid:
                year = leave_req.start_date.year
                balance = db.query(LeaveBalance).filter(
                    LeaveBalance.employee_id == leave_req.employee_id,
                    LeaveBalance.leave_type_id == leave_req.leave_type_id,
                    LeaveBalance.year == year
                ).first()

                if not balance:
                    balance = LeaveBalance(
                        employee_id=leave_req.employee_id,
                        leave_type_id=leave_req.leave_type_id,
                        year=year,
                        used_days=0.0
                    )
                    db.add(balance)

                balance.used_days += float(leave_req.working_days_count)

            # Mark days ON_LEAVE in attendance records
            settings = OrgService.get_settings(db)
            weekend_days = LeaveService._parse_weekend_days(settings.weekend_days)
            holidays = db.query(Holiday.date).filter(
                Holiday.date >= leave_req.start_date,
                Holiday.date <= leave_req.end_date
            ).all()
            holiday_dates = {h[0] for h in holidays}

            cur = leave_req.start_date
            while cur <= leave_req.end_date:
                is_weekend = cur.weekday() in weekend_days
                is_holiday = cur in holiday_dates
                if not is_weekend and not is_holiday:
                    att = db.query(Attendance).filter(
                        Attendance.employee_id == leave_req.employee_id,
                        Attendance.date == cur
                    ).first()

                    if not att:
                        att = Attendance(
                            employee_id=leave_req.employee_id,
                            date=cur,
                            status=AttendanceStatus.ON_LEAVE,
                            work_hours=0.0
                        )
                        db.add(att)
                    else:
                        att.status = AttendanceStatus.ON_LEAVE
                cur = date.fromordinal(cur.toordinal() + 1)

        # Rule: Notify the employee on every decision
        target_emp = leave_req.employee
        if target_emp and target_emp.user_id:
            notif = Notification(
                user_id=target_emp.user_id,
                message=(
                    f"Your leave request for {leave_req.start_date} to {leave_req.end_date} "
                    f"({leave_req.leave_type.name}) was {data.status.value}. "
                    f"HR Comment: {data.comment or 'No comment provided'}"
                )
            )
            db.add(notif)

        db.commit()
        db.refresh(leave_req)

        AuditService.log(
            db=db,
            actor=reviewer,
            action=f"REVIEW_LEAVE_{data.status.value}",
            entity="LeaveRequest",
            entity_id=leave_req.id,
            before=before_state,
            after={"status": data.status.value, "comment": data.comment},
            ip_address=ip_address
        )

        return LeaveRequestResponse(
            id=leave_req.id,
            employee_id=leave_req.employee_id,
            employee_code=target_emp.employee_code,
            employee_name=f"{target_emp.first_name} {target_emp.last_name}",
            leave_type_id=leave_req.leave_type_id,
            leave_type_name=leave_req.leave_type.name,
            start_date=leave_req.start_date,
            end_date=leave_req.end_date,
            working_days_count=leave_req.working_days_count,
            reason=leave_req.reason,
            status=leave_req.status.value,
            reviewed_by=leave_req.reviewed_by,
            review_comment=leave_req.review_comment,
            created_at=leave_req.created_at
        )
