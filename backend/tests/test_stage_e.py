import pytest
from app.services.ai_service import _user_request_timestamps


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


def test_ai_chat_headcount_tool_call(client, org_data):
    """Test AI assistant runs get_headcount tool and returns accurate count."""
    org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")
    org_data["create_employee"]("Ahmed", "Ali", "ahmed@saylani.ai")

    res = client.post(
        "/ai/chat",
        json={"message": "What is the total headcount of our company right now?"},
        headers=org_data["hr_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_generated"] is True
    assert "2" in data["response"] or "headcount is 2" in data["response"]
    assert "get_headcount" in data["tool_calls"]


def test_ai_employee_asking_peer_salary_refusal(client, org_data):
    """Test Employee asking for a peer's salary receives a polite refusal."""
    _, emp1_headers = org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")
    org_data["create_employee"]("Ahmed", "Ali", "ahmed@saylani.ai")

    res = client.post(
        "/ai/chat",
        json={"message": "What is Ahmed's salary?"},
        headers=emp1_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_generated"] is True
    assert "not authorized to view peer compensation details" in data["response"].lower() or "polite refusal" in data["response"].lower()


def test_ai_dashboard_summary_permissions_and_response(client, org_data):
    """Test HR & Admin can generate KPI insights; Employee gets 403 Forbidden."""
    _, emp1_headers = org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")

    kpi_payload = {
        "kpi_data": {
            "headcount": 142,
            "attendance_rate": 94.5,
            "pending_approvals": 4,
            "attrition_ytd": 2.1,
            "payroll_cost": 420000.0,
        }
    }

    # HR request -> 200 OK
    hr_res = client.post(
        "/ai/dashboard-summary",
        json=kpi_payload,
        headers=org_data["hr_headers"],
    )
    assert hr_res.status_code == 200
    hr_data = hr_res.json()
    assert hr_data["ai_generated"] is True
    assert 3 <= len(hr_data["insights"]) <= 5
    assert any("142" in i for i in hr_data["insights"])
    assert any("94.5" in i for i in hr_data["insights"])

    # Employee request -> 403 Forbidden
    emp_res = client.post(
        "/ai/dashboard-summary",
        json=kpi_payload,
        headers=emp1_headers,
    )
    assert emp_res.status_code == 403


def test_ai_smart_leave_parsing(client, org_data):
    """Test POST /ai/smart-leave parses natural language into JSON without saving."""
    _, emp1_headers = org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")

    res = client.post(
        "/ai/smart-leave",
        json={"text": "I need 2 days sick leave starting today because of fever and flu."},
        headers=emp1_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_generated"] is True
    assert data["type"] == "Sick"
    assert "start" in data and "end" in data
    assert "fever and flu" in data["reason"].lower() or len(data["reason"]) > 0

    # Ensure no leave record was committed directly
    leaves_res = client.get("/leaves", headers=emp1_headers)
    assert len(leaves_res.json()) == 0


def test_ai_policy_qa_adherence(client, org_data):
    """Test Policy Q&A answers strictly from business rules or returns 'I don't know'."""
    _, emp1_headers = org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")

    # Known rule 1: Grace period
    res1 = client.post(
        "/ai/chat",
        json={"message": "What is the office start timing and grace period?"},
        headers=emp1_headers,
    )
    assert res1.status_code == 200
    assert "09:00:00" in res1.json()["response"]
    assert "15" in res1.json()["response"]

    # Known rule 2: Half day
    res2 = client.post(
        "/ai/chat",
        json={"message": "How many hours constitute a half day?"},
        headers=emp1_headers,
    )
    assert res2.status_code == 200
    assert "4.0" in res2.json()["response"] or "4" in res2.json()["response"]

    # Unknown rule -> Strict refusal "I don't know based on company policy"
    res3 = client.post(
        "/ai/chat",
        json={"message": "Can I bring my pet dog to the office on Fridays?"},
        headers=emp1_headers,
    )
    assert res3.status_code == 200
    assert "i don't know" in res3.json()["response"].lower()


def test_ai_roman_urdu_comprehension(client, org_data):
    """Test AI assistant understands Roman Urdu and replies in Roman Urdu."""
    _, emp1_headers = org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")

    res = client.post(
        "/ai/chat",
        json={"message": "Office ka timing aur grace period kya hai?"},
        headers=emp1_headers,
    )
    assert res.status_code == 200
    resp = res.json()["response"].lower()
    # Should reply in Roman Urdu
    assert "09:00:00" in resp
    assert "minutes" in resp or "grace" in resp or "hai" in resp


def test_ai_rate_limiting(client, org_data):
    """Test rate limiting enforces maximum 20 requests per user per hour (429 Too Many Requests)."""
    _, emp1_headers = org_data["create_employee"]("Shan", "Khan", "shan@saylani.ai")
    _user_request_timestamps.clear()

    # Fire 20 requests
    for i in range(20):
        res = client.post(
            "/ai/chat",
            json={"message": f"Hello {i}"},
            headers=emp1_headers,
        )
        assert res.status_code == 200

    # 21st request should trigger 429
    res_21 = client.post(
        "/ai/chat",
        json={"message": "Exceeding request limit"},
        headers=emp1_headers,
    )
    assert res_21.status_code == 429
    assert "Rate limit" in res_21.json()["detail"]
    _user_request_timestamps.clear()
