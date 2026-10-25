from datetime import date
import pytest
from app.models.models import ApprovalStatus, Attendance, AttendanceStatus, LeaveBalance, LeaveType, Notification


@pytest.fixture
def org_data(client):
    client.post("/setup", json={
        "company_name": "Saylani Tech",
        "admin_email": "admin@saylani.org",
        "admin_password": "SuperAdminPass123!"
    })

    admin_login = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "SuperAdminPass123!"
    }).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    dept_res = client.post("/org/departments", headers=admin_headers, json={
        "name": "Engineering", "description": "Software Engineering"
    })
    dept_id = dept_res.json()["id"]

    desig_res = client.post("/org/designations", headers=admin_headers, json={
        "name": "Software Engineer", "description": "Core Developer"
    })
    desig_id = desig_res.json()["id"]

    client.post("/admin/users/hr", headers=admin_headers, json={
        "email": "hr_lead@saylani.org",
        "password": "TempHrPassword123!"
    })
    hr_login = client.post("/auth/login", json={
        "email": "hr_lead@saylani.org",
        "password": "TempHrPassword123!"
    }).json()
    hr_headers = {"Authorization": f"Bearer {hr_login['access_token']}"}
    client.post("/auth/change-password", headers=hr_headers, json={
        "current_password": "TempHrPassword123!",
        "new_password": "PermanentHrPass123!"
    })
    hr_login2 = client.post("/auth/login", json={
        "email": "hr_lead@saylani.org",
        "password": "PermanentHrPass123!"
    }).json()
    active_hr_headers = {"Authorization": f"Bearer {hr_login2['access_token']}"}

    def create_employee(first_name: str, last_name: str, email: str, salary: float = 100000.0, joining_date: str = "2026-01-01"):
        reg = client.post("/employees", headers=active_hr_headers, json={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "department_id": dept_id,
            "designation_id": desig_id,
            "joining_date": joining_date,
            "basic_salary": salary,
            "allowances": 0.0
        }).json()
        temp_pw = reg["temporary_password"]
        tok = client.post("/auth/login", json={"email": email, "password": temp_pw}).json()["access_token"]
        client.post("/auth/change-password", headers={"Authorization": f"Bearer {tok}"}, json={
            "current_password": temp_pw,
            "new_password": "PermanentPass123!"
        })
        tok2 = client.post("/auth/login", json={"email": email, "password": "PermanentPass123!"}).json()["access_token"]
        return reg, {"Authorization": f"Bearer {tok2}"}

    return {
        "admin_headers": admin_headers,
        "hr_headers": active_hr_headers,
        "dept_id": dept_id,
        "desig_id": desig_id,
        "create_employee": create_employee
    }


def test_leave_overlap_returns_422(client, org_data):
    create_employee = org_data["create_employee"]
    emp_reg, emp_headers = create_employee("Zaid", "Khan", "zaid@saylani.org")

    # Get annual leave type id
    balances = client.get("/leaves/balances", headers=emp_headers).json()
    annual_lt = next(b for b in balances if b["leave_type_name"] == "ANNUAL")

    # 1. First leave application (2026-10-05 to 2026-10-07)
    res1 = client.post("/leaves", headers=emp_headers, json={
        "leave_type_id": annual_lt["leave_type_id"],
        "start_date": "2026-10-05",
        "end_date": "2026-10-07",
        "reason": "Family trip"
    })
    assert res1.status_code == 200

    # 2. Overlapping application (2026-10-06 to 2026-10-08) -> 422
    res2 = client.post("/leaves", headers=emp_headers, json={
        "leave_type_id": annual_lt["leave_type_id"],
        "start_date": "2026-10-06",
        "end_date": "2026-10-08",
        "reason": "Overlapping request"
    })
    assert res2.status_code == 422
    assert "overlaps" in res2.json()["detail"].lower()


def test_leave_over_balance_returns_422(client, org_data):
    create_employee = org_data["create_employee"]
    emp_reg, emp_headers = create_employee("Hina", "Tariq", "hina@saylani.org")

    balances = client.get("/leaves/balances", headers=emp_headers).json()
    sick_lt = next(b for b in balances if b["leave_type_name"] == "SICK")  # Quota is 8

    # Attempt to request 15 working days for sick leave (quota is only 8)
    # 2026-10-01 to 2026-10-22 has 16 working days
    res = client.post("/leaves", headers=emp_headers, json={
        "leave_type_id": sick_lt["leave_type_id"],
        "start_date": "2026-10-01",
        "end_date": "2026-10-22",
        "reason": "Medical recovery"
    })
    assert res.status_code == 422
    assert "insufficient leave balance" in res.json()["detail"].lower()


def test_leave_skips_weekends_and_holidays(client, org_data):
    admin_headers = org_data["admin_headers"]
    create_employee = org_data["create_employee"]
    emp_reg, emp_headers = create_employee("Bilal", "Ahmed", "bilal@saylani.org")

    # Add holiday on Friday 2026-10-09
    client.post("/org/holidays", headers=admin_headers, json={
        "date": "2026-10-09",
        "name": "Iqbal Day"
    })

    balances = client.get("/leaves/balances", headers=emp_headers).json()
    casual_lt = next(b for b in balances if b["leave_type_name"] == "CASUAL")

    # Request from Thursday 2026-10-08 to Monday 2026-10-12
    # Days:
    # 10-08 (Thu): Working day (1)
    # 10-09 (Fri): Holiday (0)
    # 10-10 (Sat): Weekend (0)
    # 10-11 (Sun): Weekend (0)
    # 10-12 (Mon): Working day (1)
    # Total expected working days = 2
    res = client.post("/leaves", headers=emp_headers, json={
        "leave_type_id": casual_lt["leave_type_id"],
        "start_date": "2026-10-08",
        "end_date": "2026-10-12",
        "reason": "Short break"
    })
    assert res.status_code == 200
    assert res.json()["working_days_count"] == 2


def test_leave_approval_deducts_balance_and_marks_attendance(client, org_data, db_session):
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]
    emp_reg, emp_headers = create_employee("Sara", "Ali", "sara@saylani.org")

    balances = client.get("/leaves/balances", headers=emp_headers).json()
    annual_lt = next(b for b in balances if b["leave_type_name"] == "ANNUAL")
    initial_remaining = annual_lt["remaining_days"]

    # 1. Sara applies for 3 days (Mon 2026-10-05 to Wed 2026-10-07)
    apply_res = client.post("/leaves", headers=emp_headers, json={
        "leave_type_id": annual_lt["leave_type_id"],
        "start_date": "2026-10-05",
        "end_date": "2026-10-07",
        "reason": "Personal work"
    }).json()
    leave_id = apply_res["id"]

    # 2. HR approves leave
    review_res = client.patch(f"/leaves/{leave_id}/review", headers=hr_headers, json={
        "status": "APPROVED",
        "comment": "Approved by HR"
    })
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # 3. Verify balance deducted
    new_balances = client.get("/leaves/balances", headers=emp_headers).json()
    new_annual = next(b for b in new_balances if b["leave_type_name"] == "ANNUAL")
    assert new_annual["used_days"] == 3.0
    assert new_annual["remaining_days"] == initial_remaining - 3.0

    # 4. Verify calendar marks those days as ON_LEAVE
    cal_res = client.get(f"/attendance/calendar?employee_id={emp_reg['id']}&year=2026&month=10", headers=emp_headers)
    assert cal_res.status_code == 200
    days = {d["date"]: d["status"] for d in cal_res.json()["days"]}
    assert days["2026-10-05"] == "ON_LEAVE"
    assert days["2026-10-06"] == "ON_LEAVE"
    assert days["2026-10-07"] == "ON_LEAVE"


def test_payroll_math_and_tax_slabs(client, org_data):
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]

    # Basic salary: 100,000 -> Gross = 1.5 * 100,000 = 150,000
    # Annual Gross = 150,000 * 12 = 1,800,000
    # Tax Slab for 1.8M (1.2M to 2.4M):
    # 30,000 + 15% of (1,800,000 - 1,200,000) = 30,000 + 15% * 600,000 = 30,000 + 90,000 = 120,000
    # Monthly tax = 120,000 / 12 = 10,000
    emp_reg, _ = create_employee("Farhan", "Saeed", "farhan@saylani.org", salary=100000.0, joining_date="2026-01-01")

    # HR creates draft payroll for October 2026
    draft_res = client.post("/payroll/draft", headers=hr_headers, json={
        "year": 2026,
        "month": 10
    })
    assert draft_res.status_code == 200
    run_data = draft_res.json()
    assert run_data["status"] == "DRAFT"

    payslip = next(p for p in run_data["payslips"] if p["employee_id"] == emp_reg["id"])
    assert payslip["basic_salary"] == 100000.0
    assert payslip["gross_salary"] == 150000.0
    assert payslip["hra"] == 40000.0
    assert payslip["medical_allowance"] == 10000.0
    assert payslip["annual_gross"] == 1800000.0
    assert payslip["annual_tax"] == 120000.0
    assert payslip["monthly_tax"] == 10000.0


def test_hr_cannot_finalize_payroll(client, org_data):
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]
    create_employee("Tariq", "Jamil", "tariq@saylani.org")

    draft = client.post("/payroll/draft", headers=hr_headers, json={
        "year": 2026, "month": 10
    }).json()
    run_id = draft["id"]

    # HR attempts to finalize -> 403 Forbidden
    fin_res = client.post(f"/payroll/runs/{run_id}/finalize", headers=hr_headers)
    assert fin_res.status_code == 403
    assert "Access denied" in fin_res.json()["detail"]


def test_admin_finalizes_and_locks_payroll(client, org_data, db_session):
    admin_headers = org_data["admin_headers"]
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]
    emp_reg, _ = create_employee("Usman", "Mukhtar", "usman@saylani.org")

    draft = client.post("/payroll/draft", headers=hr_headers, json={
        "year": 2026, "month": 10
    }).json()
    run_id = draft["id"]

    # 1. Admin finalizes
    fin_res = client.post(f"/payroll/runs/{run_id}/finalize", headers=admin_headers)
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"
    assert fin_res.json()["finalized_at"] is not None

    # 2. Finalized run is locked against re-finalization
    re_fin = client.post(f"/payroll/runs/{run_id}/finalize", headers=admin_headers)
    assert re_fin.status_code == 400
    assert "already finalized and locked" in re_fin.json()["detail"].lower()

    # 3. HR cannot re-draft a finalized month
    re_draft = client.post("/payroll/draft", headers=hr_headers, json={
        "year": 2026, "month": 10
    })
    assert re_draft.status_code == 400
    assert "already finalized" in re_draft.json()["detail"].lower()

    # 4. Verify in-app notification sent to employee
    notif = db_session.query(Notification).filter(Notification.user_id == emp_reg["user_id"]).first()
    assert notif is not None
    assert "finalized" in notif.message.lower()


def test_employee_cannot_download_another_payslip(client, org_data):
    hr_headers = org_data["hr_headers"]
    admin_headers = org_data["admin_headers"]
    create_employee = org_data["create_employee"]

    emp1, emp1_headers = create_employee("Maya", "Khan", "maya@saylani.org")
    emp2, _ = create_employee("Nida", "Yasir", "nida@saylani.org")

    draft = client.post("/payroll/draft", headers=hr_headers, json={
        "year": 2026, "month": 10
    }).json()
    run_id = draft["id"]
    client.post(f"/payroll/runs/{run_id}/finalize", headers=admin_headers)

    run_details = client.get(f"/payroll/runs/{run_id}", headers=admin_headers).json()
    emp1_payslip = next(p for p in run_details["payslips"] if p["employee_id"] == emp1["id"])
    emp2_payslip = next(p for p in run_details["payslips"] if p["employee_id"] == emp2["id"])

    # 1. Maya downloads her own payslip -> 200 OK
    own_pdf = client.get(f"/payroll/payslips/{emp1_payslip['id']}/pdf", headers=emp1_headers)
    assert own_pdf.status_code == 200
    assert own_pdf.headers["content-type"] == "application/pdf"
    assert len(own_pdf.content) > 1000

    # 2. Maya attempts to download Nida's payslip -> 403 Forbidden
    other_pdf = client.get(f"/payroll/payslips/{emp2_payslip['id']}/pdf", headers=emp1_headers)
    assert other_pdf.status_code == 403
    assert "Access denied" in other_pdf.json()["detail"]
