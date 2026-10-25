from app.core.security import hash_password
from app.models.models import User, UserRole


def ensure_setup(client):
    res = client.get("/setup/status")
    if not res.json()["is_setup"]:
        client.post("/setup", json={
            "company_name": "Saylani Tech Ltd",
            "admin_email": "admin@saylani.org",
            "admin_password": "SuperAdminPass123!"
        })


def test_setup_works_once_only(client):
    # 1. Verify initially not setup
    res = client.get("/setup/status")
    assert res.status_code == 200
    assert res.json()["is_setup"] is False

    # 2. Perform setup
    setup_payload = {
        "company_name": "Saylani Tech Ltd",
        "admin_email": "admin@saylani.org",
        "admin_password": "SuperAdminPass123!"
    }
    res = client.post("/setup", json=setup_payload)
    assert res.status_code == 200
    assert "successfully completed" in res.json()["message"]

    # 3. Status should now report completed
    res = client.get("/setup/status")
    assert res.status_code == 200
    assert res.json()["is_setup"] is True
    assert res.json()["company_name"] == "Saylani Tech Ltd"

    # 4. Second setup attempt must fail with 400
    res = client.post("/setup", json=setup_payload)
    assert res.status_code == 400
    assert "already been completed" in res.json()["detail"]


def test_login_successful_and_wrong_password(client):
    ensure_setup(client)
    # Valid login
    login_res = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "SuperAdminPass123!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "ADMIN"
    assert token_data["must_change_password"] is False

    # Invalid password
    bad_res = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "WrongPassword999!"
    })
    assert bad_res.status_code == 401
    assert "Invalid email or password" in bad_res.json()["detail"]


def test_admin_creates_hr_user(client):
    ensure_setup(client)
    # Admin login
    admin_login = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "SuperAdminPass123!"
    }).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    # Admin provisions HR account
    hr_res = client.post(
        "/admin/users/hr",
        headers=admin_headers,
        json={"email": "hr@saylani.org", "password": "TempHrPassword123!"}
    )
    assert hr_res.status_code == 200
    hr_data = hr_res.json()
    assert hr_data["email"] == "hr@saylani.org"
    assert hr_data["role"] == "HR"
    assert hr_data["must_change_password"] is True


def test_must_change_password_enforced_and_resolved(client):
    ensure_setup(client)
    admin_login = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "SuperAdminPass123!"
    }).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
    client.post("/admin/users/hr", headers=admin_headers, json={
        "email": "hr@saylani.org", "password": "TempHrPassword123!"
    })

    # 1. HR logs in with temporary password
    hr_login = client.post("/auth/login", json={
        "email": "hr@saylani.org",
        "password": "TempHrPassword123!"
    }).json()
    hr_token = hr_login["access_token"]
    assert hr_login["must_change_password"] is True
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # 2. Blocked from calling normal endpoints like /auth/me
    me_res = client.get("/auth/me", headers=hr_headers)
    assert me_res.status_code == 403
    assert "Password change required" in me_res.json()["detail"]

    # 3. Can call change-password
    change_res = client.post(
        "/auth/change-password",
        headers=hr_headers,
        json={
            "current_password": "TempHrPassword123!",
            "new_password": "NewPermanentPass456!"
        }
    )
    assert change_res.status_code == 200
    assert "Password changed successfully" in change_res.json()["message"]

    # 4. Login with new password
    new_login = client.post("/auth/login", json={
        "email": "hr@saylani.org",
        "password": "NewPermanentPass456!"
    }).json()
    assert new_login["must_change_password"] is False
    new_headers = {"Authorization": f"Bearer {new_login['access_token']}"}

    # 5. /auth/me now accessible
    me_res2 = client.get("/auth/me", headers=new_headers)
    assert me_res2.status_code == 200
    assert me_res2.json()["email"] == "hr@saylani.org"
    assert me_res2.json()["must_change_password"] is False


def test_employee_blocked_from_admin_endpoints(client, db_session):
    ensure_setup(client)
    # Create an employee user directly in test db
    emp_user = User(
        email="emp@saylani.org",
        hashed_password=hash_password("EmpPass123!"),
        role=UserRole.EMPLOYEE,
        is_active=True,
        must_change_password=False
    )
    db_session.add(emp_user)
    db_session.commit()

    # Employee login
    emp_login = client.post("/auth/login", json={
        "email": "emp@saylani.org",
        "password": "EmpPass123!"
    }).json()
    emp_headers = {"Authorization": f"Bearer {emp_login['access_token']}"}

    # 1. Employee blocked from creating HR
    hr_create_res = client.post(
        "/admin/users/hr",
        headers=emp_headers,
        json={"email": "fake_hr@saylani.org", "password": "Password123!"}
    )
    assert hr_create_res.status_code == 403
    assert "Access denied" in hr_create_res.json()["detail"]

    # 2. Employee blocked from viewing audit logs
    audit_res = client.get("/audit", headers=emp_headers)
    assert audit_res.status_code == 403


def test_audit_logs_read_only_by_admin(client):
    ensure_setup(client)
    # Admin login
    admin_login = client.post("/auth/login", json={
        "email": "admin@saylani.org",
        "password": "SuperAdminPass123!"
    }).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    # Admin provisions an HR account to generate audit logs
    client.post("/admin/users/hr", headers=admin_headers, json={
        "email": "hr_audit_test@saylani.org", "password": "Password123!"
    })

    # Admin fetches audit trail
    audit_res = client.get("/audit", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    actions = [log["action"] for log in logs]
    assert "SETUP" in actions
    assert "CREATE" in actions
