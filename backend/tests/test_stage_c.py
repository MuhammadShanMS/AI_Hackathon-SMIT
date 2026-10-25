import io
from datetime import date
import pytest
from app.models.models import Attendance, AttendanceStatus, Notification, UserRole


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


def test_dashboard_numbers_match_created_records(client, org_data, db_session):
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]

    emp1, emp1_headers = create_employee("Taha", "Siddiqui", "taha@saylani.org")
    emp2, emp2_headers = create_employee("Zain", "Abbas", "zain@saylani.org")

    today = date.today()

    # Record 1 PRESENT, 1 LATE for today
    att1 = Attendance(
        employee_id=emp1["id"],
        date=today,
        status=AttendanceStatus.PRESENT,
        work_hours=8.0
    )
    att2 = Attendance(
        employee_id=emp2["id"],
        date=today,
        status=AttendanceStatus.LATE,
        work_hours=7.5
    )
    db_session.add(att1)
    db_session.add(att2)
    db_session.commit()

    # Fetch HR Dashboard
    hr_dash = client.get("/dashboard/hr", headers=hr_headers)
    assert hr_dash.status_code == 200
    data = hr_dash.json()
    assert data["headcount"] >= 2
    assert data["present_today"] == 1
    assert data["late_today"] == 1
    assert data["late_percentage"] == 50.0


def test_employee_sees_only_own_data(client, org_data):
    create_employee = org_data["create_employee"]
    emp1, emp1_headers = create_employee("Asad", "Virk", "asad@saylani.org")
    create_employee("Bilal", "Saeed", "bilal.s@saylani.org")

    emp_dash = client.get("/dashboard/employee", headers=emp1_headers)
    assert emp_dash.status_code == 200
    data = emp_dash.json()
    assert data["employee_id"] == emp1["id"]
    assert data["employee_name"] == "Asad Virk"
    assert "hours_this_week" in data
    assert "leave_balances" in data
    assert len(data["leave_balances"]) >= 4


def test_hr_cannot_read_admin_dashboard(client, org_data):
    hr_headers = org_data["hr_headers"]
    admin_headers = org_data["admin_headers"]

    # HR attempts to access Admin dashboard -> 403 Forbidden
    hr_res = client.get("/dashboard/admin", headers=hr_headers)
    assert hr_res.status_code == 403
    assert "Access denied" in hr_res.json()["detail"]

    # Admin accesses Admin dashboard -> 200 OK
    admin_res = client.get("/dashboard/admin", headers=admin_headers)
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert "headcount" in admin_data
    assert "attrition_ytd" in admin_data
    assert "payroll_cost" in admin_data
    assert "gender_distribution" in admin_data


def test_csv_dry_run_validation(client, org_data):
    hr_headers = org_data["hr_headers"]

    csv_content = """First Name,Last Name,Email,Department,Designation,Joining Date,Basic Salary
Valid,User,valid.user@saylani.org,Engineering,Software Engineer,2026-01-01,95000
Missing,Last,,Engineering,Software Engineer,2026-01-01,95000
Wrong,Dept,wrong.dept@saylani.org,NonExistentDept,Software Engineer,2026-01-01,95000
Invalid,Salary,invalid.sal@saylani.org,Engineering,Software Engineer,2026-01-01,-5000
Bad,Date,bad.date@saylani.org,Engineering,Software Engineer,32-13-2026,95000
"""
    files = {"file": ("employees.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/employees/csv/import?dry_run=true", headers=hr_headers, files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert data["imported_count"] == 0
    assert data["total_rows"] == 5
    assert data["valid_rows"] == 1
    assert data["invalid_rows"] == 4
    assert len(data["errors"]) >= 4
    fields_with_errors = [e["field"] for e in data["errors"]]
    assert "email" in fields_with_errors
    assert "department" in fields_with_errors
    assert "basic_salary" in fields_with_errors
    assert "joining_date" in fields_with_errors


def test_csv_import_success(client, org_data):
    hr_headers = org_data["hr_headers"]

    csv_content = """First Name,Last Name,Email,Department,Designation,Joining Date,Basic Salary
BulkOne,Import,bulk1@saylani.org,Engineering,Software Engineer,2026-01-01,90000
BulkTwo,Import,bulk2@saylani.org,Engineering,Software Engineer,2026-01-01,95000
"""
    files = {"file": ("bulk.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/employees/csv/import?dry_run=false", headers=hr_headers, files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is False
    assert data["imported_count"] == 2
    assert len(data["errors"]) == 0

    # Verify employees can be queried
    dir_res = client.get("/employees?search=BulkOne", headers=hr_headers)
    assert dir_res.status_code == 200
    assert dir_res.json()["total"] >= 1


def test_announcement_permissions_and_notifications(client, org_data):
    admin_headers = org_data["admin_headers"]
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]
    emp_reg, emp_headers = create_employee("Faraz", "Khan", "faraz@saylani.org")

    # 1. Admin publishes announcement -> 200
    res_admin = client.post("/announcements", headers=admin_headers, json={
        "title": "Annual Company Dinner",
        "body": "Dinner will be held next Friday at 8 PM."
    })
    assert res_admin.status_code == 200

    # 2. HR publishes announcement -> 200
    res_hr = client.post("/announcements", headers=hr_headers, json={
        "title": "Health Insurance Renewal",
        "body": "Please submit your medical forms by end of the week."
    })
    assert res_hr.status_code == 200

    # 3. Employee attempts to publish announcement -> 403 Forbidden
    res_emp = client.post("/announcements", headers=emp_headers, json={
        "title": "Unauthorized Post",
        "body": "This should be blocked."
    })
    assert res_emp.status_code == 403

    # 4. Employee reads announcements -> 200
    list_res = client.get("/announcements", headers=emp_headers)
    assert list_res.status_code == 200
    titles = [a["title"] for a in list_res.json()]
    assert "Annual Company Dinner" in titles
    assert "Health Insurance Renewal" in titles


def test_notification_flow(client, org_data, db_session):
    create_employee = org_data["create_employee"]
    emp_reg, emp_headers = create_employee("Danish", "Taimoor", "danish@saylani.org")

    # Manually add 2 notifications for Danish
    n1 = Notification(user_id=emp_reg["user_id"], message="Welcome to HCM Lite!", is_read=False)
    n2 = Notification(user_id=emp_reg["user_id"], message="Payroll draft generated.", is_read=False)
    db_session.add(n1)
    db_session.add(n2)
    db_session.commit()

    # 1. List notifications
    notifs_res = client.get("/notifications", headers=emp_headers)
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    assert len(notifs) >= 2
    assert notifs[0]["is_read"] is False

    # 2. Mark one as read
    target_id = notifs[0]["id"]
    read_res = client.patch(f"/notifications/{target_id}/read", headers=emp_headers)
    assert read_res.status_code == 200

    # 3. Mark all as read
    read_all = client.post("/notifications/read-all", headers=emp_headers)
    assert read_all.status_code == 200

    # Verify all are read
    notifs_after = client.get("/notifications", headers=emp_headers).json()
    assert all(n["is_read"] is True for n in notifs_after)
