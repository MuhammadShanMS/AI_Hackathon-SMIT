from datetime import date
import pytest
from app.models.models import ApprovalStatus, AttendanceStatus, Notification


@pytest.fixture
def org_data(client):
    # Setup company
    client.post("/setup", json={
        "company_name": "Saylani Tech",
        "admin_email": "admin@saylani.org",
        "admin_password": "SuperAdminPass123!"
    })

    # Admin Login
    admin_login = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "SuperAdminPass123!"
    }).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    # Create Department & Designation
    dept_res = client.post("/org/departments", headers=admin_headers, json={
        "name": "Engineering", "description": "Software Engineering Dept"
    })
    dept_id = dept_res.json()["id"]

    desig_res = client.post("/org/designations", headers=admin_headers, json={
        "name": "Software Engineer", "description": "Core Developer"
    })
    desig_id = desig_res.json()["id"]

    # Admin creates HR
    client.post("/admin/users/hr", headers=admin_headers, json={
        "email": "hr_manager@saylani.org",
        "password": "TempHrPassword123!"
    })
    # Login as HR and rotate password
    hr_login = client.post("/auth/login", json={
        "email": "hr_manager@saylani.org",
        "password": "TempHrPassword123!"
    }).json()
    hr_headers = {"Authorization": f"Bearer {hr_login['access_token']}"}
    client.post("/auth/change-password", headers=hr_headers, json={
        "current_password": "TempHrPassword123!",
        "new_password": "NewPermanentHrPass123!"
    })
    hr_login2 = client.post("/auth/login", json={
        "email": "hr_manager@saylani.org",
        "password": "NewPermanentHrPass123!"
    }).json()
    active_hr_headers = {"Authorization": f"Bearer {hr_login2['access_token']}"}

    def create_employee(first_name: str, last_name: str, email: str, salary: float = 80000.0, allowances: float = 10000.0, joining_date: str = "2026-01-01"):
        reg = client.post("/employees", headers=active_hr_headers, json={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "department_id": dept_id,
            "designation_id": desig_id,
            "joining_date": joining_date,
            "basic_salary": salary,
            "allowances": allowances
        }).json()
        temp_pw = reg["temporary_password"]
        # Login and rotate password
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


def test_hr_register_creates_login_and_balances(client, org_data):
    hr_headers = org_data["hr_headers"]

    # HR registers Alice
    reg_res = client.post("/employees", headers=hr_headers, json={
        "email": "alice@saylani.org",
        "first_name": "Alice",
        "last_name": "Smith",
        "phone": "+92-300-1112233",
        "address": "Karachi, Pakistan",
        "department_id": org_data["dept_id"],
        "designation_id": org_data["desig_id"],
        "joining_date": "2026-01-01",
        "basic_salary": 85000.0,
        "allowances": 15000.0
    })
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "EMP-" in reg_data["employee_code"]
    assert len(reg_data["temporary_password"]) >= 8

    # HR views Alice's 360 profile to verify auto-created leave balances
    alice_id = reg_data["id"]
    profile_res = client.get(f"/employees/{alice_id}", headers=hr_headers)
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert len(profile["leave_balances"]) >= 4
    leave_names = [lb["leave_type_name"] for lb in profile["leave_balances"]]
    assert "ANNUAL" in leave_names
    assert "SICK" in leave_names
    assert "CASUAL" in leave_names


def test_employee_scope_blocked_from_another_profile(client, org_data):
    create_employee = org_data["create_employee"]
    bob_reg, bob_headers = create_employee("Bob", "Marley", "bob@saylani.org")
    charlie_reg, _ = create_employee("Charlie", "Brown", "charlie@saylani.org")

    # 1. Bob reads own profile -> 200 OK
    own_res = client.get(f"/employees/{bob_reg['id']}", headers=bob_headers)
    assert own_res.status_code == 200
    assert own_res.json()["first_name"] == "Bob"

    # 2. Bob attempts to read Charlie's profile -> 403 Forbidden
    other_res = client.get(f"/employees/{charlie_reg['id']}", headers=bob_headers)
    assert other_res.status_code == 403
    assert "Access denied" in other_res.json()["detail"]


def test_employee_cannot_see_other_salary(client, org_data):
    create_employee = org_data["create_employee"]
    bob_reg, bob_headers = create_employee("Bob", "Marley", "bob@saylani.org")
    charlie_reg, _ = create_employee("Charlie", "Brown", "charlie@saylani.org", salary=120000.0)

    # Bob views directory
    dir_res = client.get("/employees", headers=bob_headers)
    assert dir_res.status_code == 200
    items = dir_res.json()["items"]

    for item in items:
        if item["email"] == "charlie@saylani.org":
            # Must not see Charlie's salary
            assert item["basic_salary"] is None
            assert item["allowances"] is None
        elif item["email"] == "bob@saylani.org":
            # Can see own salary
            assert item["basic_salary"] is not None


def test_salary_structure_editable_by_hr_only(client, org_data):
    admin_headers = org_data["admin_headers"]
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]
    bob_reg, _ = create_employee("Bob", "Marley", "bob@saylani.org")
    bob_id = bob_reg["id"]

    # 1. Admin attempts to edit salary structure -> 403 Forbidden (view-only for Admin)
    admin_patch = client.patch(f"/employees/{bob_id}", headers=admin_headers, json={
        "basic_salary": 120000.0
    })
    assert admin_patch.status_code == 403
    assert "Access denied" in admin_patch.json()["detail"]

    # 2. HR edits salary structure -> 200 OK
    hr_patch = client.patch(f"/employees/{bob_id}", headers=hr_headers, json={
        "basic_salary": 115000.0,
        "allowances": 20000.0
    })
    assert hr_patch.status_code == 200
    assert hr_patch.json()["basic_salary"] == 115000.0
    assert hr_patch.json()["allowances"] == 20000.0


def test_duplicate_check_in_conflict(client, org_data):
    create_employee = org_data["create_employee"]
    _, bob_headers = create_employee("Bob", "Marley", "bob@saylani.org")

    # First check-in
    first_res = client.post("/attendance/check-in", headers=bob_headers, json={
        "latitude": 24.8607, "longitude": 67.0011
    })
    assert first_res.status_code == 200
    assert first_res.json()["status"] in ["PRESENT", "LATE"]

    # Second check-in on the same day -> 409 Conflict
    dup_res = client.post("/attendance/check-in", headers=bob_headers, json={})
    assert dup_res.status_code == 409
    assert "already been recorded for today" in dup_res.json()["detail"]


def test_half_day_status_on_checkout(client, org_data):
    create_employee = org_data["create_employee"]
    _, bob_headers = create_employee("Bob", "Marley", "bob@saylani.org")

    # Check-in
    client.post("/attendance/check-in", headers=bob_headers, json={})

    # Bob checks out immediately (work_hours < 5.0h)
    co_res = client.post("/attendance/check-out", headers=bob_headers, json={})
    assert co_res.status_code == 200
    data = co_res.json()
    assert data["check_out_time"] is not None
    assert data["status"] == "HALF_DAY"


def test_late_check_in_status(client, org_data):
    admin_headers = org_data["admin_headers"]
    create_employee = org_data["create_employee"]
    _, dave_headers = create_employee("Dave", "Miller", "dave@saylani.org")

    # Set office start time to 00:01 with grace 1 min (cutoff 00:02) so Dave's daytime punch is late
    client.put("/org/settings", headers=admin_headers, json={
        "office_start_time": "00:01",
        "grace_period_minutes": 1
    })

    ci_res = client.post("/attendance/check-in", headers=dave_headers, json={})
    assert ci_res.status_code == 200
    assert ci_res.json()["status"] == "LATE"

    # Reset office start time back to 09:00, grace 15
    client.put("/org/settings", headers=admin_headers, json={
        "office_start_time": "09:00",
        "grace_period_minutes": 15
    })


def test_absent_calculation_skips_weekends_and_holidays(client, org_data):
    admin_headers = org_data["admin_headers"]
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]

    # Add a public holiday on 2026-10-14
    client.post("/org/holidays", headers=admin_headers, json={
        "date": "2026-10-14",
        "name": "Mid-Month Festival"
    })

    charlie_reg, _ = create_employee("Charlie", "Brown", "charlie@saylani.org", joining_date="2026-01-01")
    charlie_id = charlie_reg["id"]

    # Fetch October 2026 monthly attendance calendar for Charlie
    cal_res = client.get(f"/attendance/calendar?employee_id={charlie_id}&year=2026&month=10", headers=hr_headers)
    assert cal_res.status_code == 200
    cal_data = cal_res.json()

    days_by_date = {d["date"]: d["status"] for d in cal_data["days"]}

    # 1. 2026-10-14 was marked as public holiday -> must be HOLIDAY (not ABSENT)
    assert days_by_date["2026-10-14"] == "HOLIDAY"

    # 2. 2026-10-10 is Saturday -> must be WEEKEND (not ABSENT)
    assert days_by_date["2026-10-10"] == "WEEKEND"

    # 3. 2026-10-11 is Sunday -> must be WEEKEND (not ABSENT)
    assert days_by_date["2026-10-11"] == "WEEKEND"

    # 4. 2026-10-06 is a regular Tuesday with no attendance -> must be ABSENT
    assert days_by_date["2026-10-06"] == "ABSENT"


def test_correction_flow_updates_attendance_and_notifies(client, org_data, db_session):
    hr_headers = org_data["hr_headers"]
    create_employee = org_data["create_employee"]
    bob_reg, bob_headers = create_employee("Bob", "Marley", "bob@saylani.org")
    bob_id = bob_reg["id"]

    # 1. Bob submits correction request for 2026-10-05
    corr_res = client.post("/attendance/corrections", headers=bob_headers, json={
        "date": "2026-10-05",
        "requested_check_in": "2026-10-05T09:00:00Z",
        "requested_check_out": "2026-10-05T18:00:00Z",
        "reason": "Biometric device scanner malfunction"
    })
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    corr_id = corr_data["id"]
    assert corr_data["status"] == "PENDING"

    # 2. HR reviews and approves
    review_res = client.patch(f"/attendance/corrections/{corr_id}/review", headers=hr_headers, json={
        "status": "APPROVED",
        "comment": "Verified with security log"
    })
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # 3. Verify attendance record was created/updated with correct times and status
    cal_res = client.get(f"/attendance/calendar?employee_id={bob_id}&year=2026&month=10", headers=hr_headers)
    assert cal_res.status_code == 200
    day_05 = next(d for d in cal_res.json()["days"] if d["date"] == "2026-10-05")
    assert day_05["status"] == "PRESENT"
    assert day_05["work_hours"] == 9.0

    # 4. Verify in-app notification was generated for Bob
    notif = db_session.query(Notification).filter(Notification.user_id == bob_reg["user_id"]).first()
    assert notif is not None
    assert "APPROVED" in notif.message
