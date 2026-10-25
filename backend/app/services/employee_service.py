import secrets
import string
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.security import hash_password
from app.models.models import User, UserRole, Employee, Department, Designation, LeaveType, LeaveBalance
from app.schemas.employee import (
    EmployeeRegisterRequest, EmployeeRegisterResponse,
    EmployeeDirectoryItem, EmployeeDirectoryResponse,
    Employee360Profile, LeaveBalanceSummary,
    EmployeeSelfUpdate, EmployeeHRUpdate
)
from app.services.audit_service import AuditService


class EmployeeService:
    @staticmethod
    def _generate_temp_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        # Ensure at least one uppercase, one digit, one special
        pwd = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*")
        ]
        pwd += [secrets.choice(alphabet) for _ in range(length - 4)]
        secrets.SystemRandom().shuffle(pwd)
        return "".join(pwd)

    @staticmethod
    def register_employee(
        db: Session,
        actor: User,
        data: EmployeeRegisterRequest,
        ip_address: Optional[str] = None
    ) -> EmployeeRegisterResponse:
        clean_email = data.email.strip().lower()
        existing_user = db.query(User).filter(User.email == clean_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{clean_email}' already exists."
            )

        dept = db.query(Department).filter(Department.id == data.department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found.")

        desig = db.query(Designation).filter(Designation.id == data.designation_id).first()
        if not desig:
            raise HTTPException(status_code=404, detail="Designation not found.")

        temp_password = EmployeeService._generate_temp_password()

        # 1. Create User account
        new_user = User(
            email=clean_email,
            hashed_password=hash_password(temp_password),
            role=UserRole.EMPLOYEE,
            is_active=True,
            must_change_password=True
        )
        db.add(new_user)
        db.flush()

        # 2. Generate employee code
        next_id = (db.query(Employee).count()) + 1
        emp_code = f"EMP-{next_id:04d}"
        # Ensure uniqueness
        while db.query(Employee).filter(Employee.employee_code == emp_code).first() is not None:
            next_id += 1
            emp_code = f"EMP-{next_id:04d}"

        # 3. Create Employee profile
        employee = Employee(
            user_id=new_user.id,
            employee_code=emp_code,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            phone=data.phone.strip() if data.phone else None,
            address=data.address.strip() if data.address else None,
            department_id=data.department_id,
            designation_id=data.designation_id,
            joining_date=data.joining_date,
            basic_salary=data.basic_salary,
            allowances=data.allowances
        )
        db.add(employee)
        db.flush()

        # 4. Auto-create leave balances for current year
        year = data.joining_date.year
        leave_types = db.query(LeaveType).all()
        for lt in leave_types:
            balance = LeaveBalance(
                employee_id=employee.id,
                leave_type_id=lt.id,
                year=year,
                used_days=0.0
            )
            db.add(balance)

        db.commit()
        db.refresh(employee)
        db.refresh(new_user)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_EMPLOYEE",
            entity="Employee",
            entity_id=employee.id,
            after={
                "employee_code": employee.employee_code,
                "email": new_user.email,
                "name": f"{employee.first_name} {employee.last_name}",
                "department": dept.name,
                "designation": desig.name,
                "basic_salary": float(employee.basic_salary)
            },
            ip_address=ip_address
        )

        return EmployeeRegisterResponse(
            id=employee.id,
            user_id=new_user.id,
            employee_code=employee.employee_code,
            email=new_user.email,
            first_name=employee.first_name,
            last_name=employee.last_name,
            department_id=employee.department_id,
            designation_id=employee.designation_id,
            temporary_password=temp_password,
            message="Employee registered successfully. Provide temporary credentials to employee."
        )

    @staticmethod
    def list_employees(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        department_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> EmployeeDirectoryResponse:
        query = db.query(Employee).join(User, Employee.user_id == User.id)

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(s),
                    Employee.last_name.ilike(s),
                    Employee.employee_code.ilike(s),
                    User.email.ilike(s)
                )
            )

        if department_id:
            query = query.filter(Employee.department_id == department_id)

        if status_filter:
            if status_filter.lower() == "active":
                query = query.filter(User.is_active == True)
            elif status_filter.lower() == "inactive":
                query = query.filter(User.is_active == False)

        total = query.count()
        employees = query.order_by(Employee.id.asc()).offset(offset).limit(limit).all()

        is_employee_role = current_user.role == UserRole.EMPLOYEE

        items = []
        for emp in employees:
            # Rule: Employee cannot see others' salary
            can_see_salary = not is_employee_role or (
                current_user.employee and current_user.employee.id == emp.id
            )

            items.append(
                EmployeeDirectoryItem(
                    id=emp.id,
                    employee_code=emp.employee_code,
                    first_name=emp.first_name,
                    last_name=emp.last_name,
                    email=emp.user.email,
                    phone=emp.phone,
                    department_id=emp.department_id,
                    department_name=emp.department.name if emp.department else "",
                    designation_id=emp.designation_id,
                    designation_name=emp.designation.name if emp.designation else "",
                    joining_date=emp.joining_date,
                    is_active=emp.user.is_active,
                    basic_salary=float(emp.basic_salary) if can_see_salary else None,
                    allowances=float(emp.allowances) if can_see_salary else None
                )
            )

        return EmployeeDirectoryResponse(total=total, items=items)

    @staticmethod
    def get_employee_360(
        db: Session,
        current_user: User,
        employee_id: int
    ) -> Employee360Profile:
        # Rule: Employee can only read their own profile
        if current_user.role == UserRole.EMPLOYEE:
            if not current_user.employee or current_user.employee.id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view your own employee profile."
                )

        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found.")

        # Leave balances
        balances = []
        for lb in emp.leave_balances:
            quota = lb.leave_type.yearly_quota
            rem = max(0.0, float(quota) - float(lb.used_days))
            balances.append(
                LeaveBalanceSummary(
                    leave_type_name=lb.leave_type.name,
                    yearly_quota=quota,
                    used_days=float(lb.used_days),
                    remaining_days=rem
                )
            )

        # Salary visibility: Employee sees own salary, HR/Admin sees salary
        is_employee_role = current_user.role == UserRole.EMPLOYEE
        can_see_salary = not is_employee_role or (
            current_user.employee and current_user.employee.id == emp.id
        )

        return Employee360Profile(
            id=emp.id,
            user_id=emp.user_id,
            employee_code=emp.employee_code,
            first_name=emp.first_name,
            last_name=emp.last_name,
            email=emp.user.email,
            phone=emp.phone,
            address=emp.address,
            department_id=emp.department_id,
            department_name=emp.department.name if emp.department else "",
            designation_id=emp.designation_id,
            designation_name=emp.designation.name if emp.designation else "",
            joining_date=emp.joining_date,
            exit_date=emp.exit_date,
            is_active=emp.user.is_active,
            basic_salary=float(emp.basic_salary) if can_see_salary else None,
            allowances=float(emp.allowances) if can_see_salary else None,
            leave_balances=balances
        )

    @staticmethod
    def update_self_profile(
        db: Session,
        current_user: User,
        employee_id: int,
        data: EmployeeSelfUpdate,
        ip_address: Optional[str] = None
    ) -> Employee360Profile:
        if not current_user.employee or current_user.employee.id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only edit your own profile."
            )

        emp = current_user.employee
        before_state = {"phone": emp.phone, "address": emp.address}
        if data.phone is not None:
            emp.phone = data.phone.strip() if data.phone else None
        if data.address is not None:
            emp.address = data.address.strip() if data.address else None

        db.commit()
        db.refresh(emp)

        AuditService.log(
            db=db,
            actor=current_user,
            action="UPDATE_SELF_PROFILE",
            entity="Employee",
            entity_id=emp.id,
            before=before_state,
            after={"phone": emp.phone, "address": emp.address},
            ip_address=ip_address
        )
        return EmployeeService.get_employee_360(db, current_user, emp.id)

    @staticmethod
    def update_employee_by_hr(
        db: Session,
        actor: User,
        employee_id: int,
        data: EmployeeHRUpdate,
        ip_address: Optional[str] = None
    ) -> Employee360Profile:
        # Rule: Admin view only; Salary structure editable by HR only
        if actor.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Salary structure and employee records are editable by HR only. Admin has view-only rights."
            )
        if actor.role != UserRole.HR:
            raise HTTPException(status_code=403, detail="Access denied: Requires HR role.")

        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found.")

        before_state = {
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "phone": emp.phone,
            "address": emp.address,
            "department_id": emp.department_id,
            "designation_id": emp.designation_id,
            "basic_salary": float(emp.basic_salary),
            "allowances": float(emp.allowances)
        }

        update_dict = data.model_dump(exclude_unset=True)
        if "department_id" in update_dict and update_dict["department_id"]:
            if not db.query(Department).filter(Department.id == update_dict["department_id"]).first():
                raise HTTPException(status_code=404, detail="Department not found.")
        if "designation_id" in update_dict and update_dict["designation_id"]:
            if not db.query(Designation).filter(Designation.id == update_dict["designation_id"]).first():
                raise HTTPException(status_code=404, detail="Designation not found.")

        for key, value in update_dict.items():
            setattr(emp, key, value)

        db.commit()
        db.refresh(emp)

        AuditService.log(
            db=db,
            actor=actor,
            action="UPDATE_EMPLOYEE",
            entity="Employee",
            entity_id=emp.id,
            before=before_state,
            after=update_dict,
            ip_address=ip_address
        )
        return EmployeeService.get_employee_360(db, actor, emp.id)
