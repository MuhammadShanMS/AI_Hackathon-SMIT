import csv
import io
import re
from datetime import date
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import User, UserRole, Employee, Department, Designation
from app.schemas.csv_schemas import CSVImportErrorItem, CSVImportResponse
from app.schemas.employee import EmployeeRegisterRequest
from app.services.employee_service import EmployeeService


class CSVService:
    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @staticmethod
    def export_employees(db: Session, actor: User) -> tuple[str, str]:
        # Rule: HR export of employees (Admin also permitted)
        if actor.role not in (UserRole.HR, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only HR and Administrators can export employee data."
            )

        employees = db.query(Employee).join(User, Employee.user_id == User.id).order_by(Employee.id.asc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Employee Code", "First Name", "Last Name", "Email", "Phone",
            "Gender", "Address", "Department", "Designation", "Joining Date",
            "Basic Salary", "Allowances", "Status"
        ])

        for e in employees:
            writer.writerow([
                e.employee_code,
                e.first_name,
                e.last_name,
                e.user.email if e.user else "",
                e.phone or "",
                e.gender or "Unspecified",
                e.address or "",
                e.department.name if e.department else "",
                e.designation.name if e.designation else "",
                str(e.joining_date),
                float(e.basic_salary),
                float(e.allowances),
                "Active" if (e.user and e.user.is_active) else "Inactive"
            ])

        csv_str = output.getvalue()
        output.close()
        filename = f"employees_export_{date.today().isoformat()}.csv"
        return csv_str, filename

    @staticmethod
    def import_employees(
        db: Session,
        actor: User,
        csv_content: str,
        dry_run: bool = True,
        ip_address: Optional[str] = None
    ) -> CSVImportResponse:
        # Rule: HR import
        if actor.role not in (UserRole.HR, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only HR and Administrators can import employee data."
            )

        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="Invalid CSV: Empty file or headers missing.")

        # Normalize field headers (lowercase, strip whitespace)
        field_map = {name.lower().replace(" ", "_"): name for name in reader.fieldnames}

        # Cache existing departments & designations
        departments = {d.name.lower(): d for d in db.query(Department).all()}
        designations = {d.name.lower(): d for d in db.query(Designation).all()}

        # Cache existing emails & codes
        existing_emails = {u.email.lower() for u in db.query(User.email).all()}
        existing_codes = {e.employee_code.lower() for e in db.query(Employee.employee_code).all()}

        file_emails = set()
        file_codes = set()
        errors: list[CSVImportErrorItem] = []
        valid_rows: list[dict] = []
        row_number = 1

        for row_dict in reader:
            row_number += 1
            # Helper to extract value by multiple possible header names
            def get_val(*aliases):
                for a in aliases:
                    for actual_name in reader.fieldnames:
                        if actual_name.lower().replace(" ", "_").strip() == a:
                            return (row_dict[actual_name] or "").strip()
                return ""

            first_name = get_val("first_name", "firstname")
            last_name = get_val("last_name", "lastname")
            email = get_val("email", "email_address")
            dept_name = get_val("department", "dept")
            desig_name = get_val("designation", "role", "title")
            joining_str = get_val("joining_date", "join_date", "date_of_joining")
            salary_str = get_val("basic_salary", "salary")
            allowance_str = get_val("allowances", "allowance")
            emp_code = get_val("employee_code", "code")
            phone = get_val("phone", "phone_number")
            address = get_val("address")
            gender = get_val("gender")

            row_has_error = False

            # 1. Required fields
            if not first_name:
                errors.append(CSVImportErrorItem(row=row_number, field="first_name", reason="First name is required."))
                row_has_error = True
            if not last_name:
                errors.append(CSVImportErrorItem(row=row_number, field="last_name", reason="Last name is required."))
                row_has_error = True

            # 2. Valid and unique email
            if not email:
                errors.append(CSVImportErrorItem(row=row_number, field="email", reason="Email is required."))
                row_has_error = True
            elif not CSVService.EMAIL_REGEX.match(email):
                errors.append(CSVImportErrorItem(row=row_number, field="email", reason="Invalid email format."))
                row_has_error = True
            elif email.lower() in existing_emails or email.lower() in file_emails:
                errors.append(CSVImportErrorItem(row=row_number, field="email", reason=f"Email '{email}' is already registered."))
                row_has_error = True
            else:
                file_emails.add(email.lower())

            # 3. Unique employee code if provided
            if emp_code:
                if emp_code.lower() in existing_codes or emp_code.lower() in file_codes:
                    errors.append(CSVImportErrorItem(row=row_number, field="employee_code", reason=f"Employee code '{emp_code}' is already in use."))
                    row_has_error = True
                else:
                    file_codes.add(emp_code.lower())

            # 4. Known department
            dept = departments.get(dept_name.lower())
            if not dept:
                errors.append(CSVImportErrorItem(row=row_number, field="department", reason=f"Unknown department '{dept_name}'."))
                row_has_error = True

            # 5. Known designation (or auto-create if missing, but let's check or pick first/match)
            desig = designations.get(desig_name.lower())
            if not desig:
                if designations:
                    desig = next(iter(designations.values()))
                else:
                    desig = Designation(name=desig_name or "Staff")
                    db.add(desig)
                    db.flush()
                    designations[desig.name.lower()] = desig

            # 6. ISO Date
            joining_date = None
            if not joining_str:
                errors.append(CSVImportErrorItem(row=row_number, field="joining_date", reason="Joining date is required."))
                row_has_error = True
            else:
                try:
                    joining_date = date.fromisoformat(joining_str)
                except ValueError:
                    errors.append(CSVImportErrorItem(row=row_number, field="joining_date", reason="Date must be in ISO format (YYYY-MM-DD)."))
                    row_has_error = True

            # 7. Salary > 0
            basic_salary = 0.0
            if not salary_str:
                errors.append(CSVImportErrorItem(row=row_number, field="basic_salary", reason="Basic salary is required."))
                row_has_error = True
            else:
                try:
                    basic_salary = float(salary_str)
                    if basic_salary <= 0:
                        errors.append(CSVImportErrorItem(row=row_number, field="basic_salary", reason="Basic salary must be greater than 0."))
                        row_has_error = True
                except ValueError:
                    errors.append(CSVImportErrorItem(row=row_number, field="basic_salary", reason="Salary must be a valid numeric amount."))
                    row_has_error = True

            allowances = 0.0
            if allowance_str:
                try:
                    allowances = float(allowance_str)
                except ValueError:
                    allowances = 0.0

            if not row_has_error:
                valid_rows.append({
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "address": address,
                    "gender": gender or "Unspecified",
                    "department_id": dept.id,
                    "designation_id": desig.id,
                    "joining_date": joining_date,
                    "basic_salary": basic_salary,
                    "allowances": allowances
                })

        total_rows = row_number - 1
        invalid_rows = len(set(e.row for e in errors))
        imported_count = 0

        # If not dry run and no fatal errors, insert records
        if not dry_run and not errors:
            for item in valid_rows:
                req = EmployeeRegisterRequest(
                    email=item["email"],
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    phone=item["phone"],
                    address=item["address"],
                    department_id=item["department_id"],
                    designation_id=item["designation_id"],
                    joining_date=item["joining_date"],
                    basic_salary=item["basic_salary"],
                    allowances=item["allowances"]
                )
                EmployeeService.register_employee(db, actor, req, ip_address=ip_address)
                imported_count += 1

        return CSVImportResponse(
            total_rows=total_rows,
            valid_rows=len(valid_rows),
            invalid_rows=invalid_rows,
            dry_run=dry_run,
            imported_count=imported_count,
            errors=errors
        )
