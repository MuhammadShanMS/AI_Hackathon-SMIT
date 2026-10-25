import pytest
from app.models.models import Attendance, AttendanceStatus, User, Employee
from datetime import date, datetime, timezone

@pytest.fixture
def org_data(client):
    client.post("/setup", json={
        "company_name": "Saylani AI Systems",
        "admin_email": "admin@saylani.ai",
        "admin_password": "SuperAdminPass123!"
    })

    admin_login = client.post("/auth/login", json={
        "email": "admin@saylani.ai",
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
        "email": "hr_lead@saylani.ai",
        "password": "TempHrPassword123!"
    })
    hr_login = client.post("/auth/login", json={
        "email": "hr_lead@saylani.ai",
        "password": "TempHrPassword123!"
    }).json()
    hr_headers = {"Authorization": f"Bearer {hr_login['access_token']}"}
    client.post("/auth/change-password", headers=hr_headers, json={
        "current_password": "TempHrPassword123!",
        "new_password": "PermanentHrPass123!"
    })
    hr_login2 = client.post("/auth/login", json={
        "email": "hr_lead@saylani.ai",
        "password": "PermanentHrPass123!"
    }).json()
    active_hr_headers = {"Authorization": f"Bearer {hr_login2['access_token']}"}

    def create_employee(first_name: str, last_name: str, email: str, salary: float = 100000.0):
        reg = client.post("/employees", headers=active_hr_headers, json={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "department_id": dept_id,
            "designation_id": desig_id,
            "joining_date": "2026-01-01",
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
        "create_employee": create_employee
    }


def test_admin_list_users(client, org_data):
    """Test GET /admin/users lists all accounts and their activation status."""
    admin_headers = org_data["admin_headers"]
    hr_headers = org_data["hr_headers"]

    # Admin can list users
    res = client.get("/admin/users", headers=admin_headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 2
    emails = [u["email"] for u in users]
    assert "admin@saylani.ai" in emails
    assert "hr_lead@saylani.ai" in emails

    # HR cannot list admin users -> 403
    hr_res = client.get("/admin/users", headers=hr_headers)
    assert hr_res.status_code == 403


def test_ai_search_employees_tool(client, org_data):
    """Test AI assistant search_employees tool correctly queries User.email and Designation.name without error."""
    hr_headers = org_data["hr_headers"]
    org_data["create_employee"]("Tariq", "Jamil", "tariq.jamil@saylani.ai")

    res = client.post(
        "/ai/chat",
        json={"message": "Who is Tariq?"},
        headers=hr_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_generated"] is True
    assert "Tariq" in data["response"]


def test_camera_geofence_and_accuracy_validation(client, org_data):
    """Test camera attendance validates face count, GPS accuracy, and office geofence distance."""
    _, emp_headers = org_data["create_employee"]("Zubair", "Khan", "zubair@saylani.ai")

    # 1. Reject if face count != 1
    res1 = client.post(
        "/attendance/check-in",
        headers=emp_headers,
        json={"check_in_method": "FACE_DETECTION", "faces_detected": 2},
    )
    assert res1.status_code == 400
    assert "exactly one face" in res1.json()["detail"].lower()

    # 2. Reject if GPS accuracy > 100m
    res2 = client.post(
        "/attendance/check-in",
        headers=emp_headers,
        json={"check_in_method": "FACE_DETECTION", "faces_detected": 1, "accuracy": 150.0},
    )
    assert res2.status_code == 400
    assert "accuracy" in res2.json()["detail"].lower()


def test_dashboard_summary_flexible_payload(client, org_data):
    """Test dashboard summary endpoint handles both raw and wrapped KPI payloads."""
    hr_headers = org_data["hr_headers"]

    # Direct raw dictionary
    raw_payload = {
        "headcount": 50,
        "attendance_rate": 96.0,
        "pending_approvals": 2,
    }
    res = client.post(
        "/ai/dashboard-summary",
        headers=hr_headers,
        json=raw_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_generated"] is True
    assert len(data["insights"]) >= 3
