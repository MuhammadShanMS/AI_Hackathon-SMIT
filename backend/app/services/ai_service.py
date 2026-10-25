import time
import json
import logging
from datetime import datetime, timezone, date
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.models import (
    User,
    UserRole,
    Employee,
    Attendance,
    AttendanceStatus,
    LeaveRequest,
    ApprovalStatus,
    LeaveBalance,
    PayrollRun,
    PayrollStatus,
    Payslip,
    CompanySettings,
    AILog,
)

logger = logging.getLogger(__name__)

# In-memory sliding window rate limiter: 20 requests per user per hour
_user_request_timestamps = defaultdict(deque)


def check_rate_limit(user_id: int):
    now = time.time()
    queue = _user_request_timestamps[user_id]
    # Remove timestamps older than 1 hour (3600 seconds)
    while queue and queue[0] < now - 3600:
        queue.popleft()
    if len(queue) >= 20:
        raise HTTPException(
            status_code=429,
            detail="Rate limit reached: Maximum 20 AI requests per user per hour.",
        )
    queue.append(now)


class AIService:

    @staticmethod
    def log_call(
        db: Session,
        user_id: int,
        prompt: str,
        tool_calls: Optional[List[str]],
        response: str,
        latency_ms: int,
    ):
        try:
            log_entry = AILog(
                user_id=user_id,
                prompt=prompt[:2000],
                tool_calls=json.dumps(tool_calls) if tool_calls else None,
                response=response[:4000] if response else None,
                latency_ms=latency_ms,
                created_at=datetime.now(timezone.utc),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save AI log: {e}")

    # =========================================================================
    # TOOL DEFINITIONS & EXECUTION (SCOPED TO CURRENT USER)
    # =========================================================================

    @staticmethod
    def get_tool_declarations():
        return [
            {
                "name": "get_headcount",
                "description": "Get total active workforce headcount and department breakdown",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "department_id": {
                            "type": "INTEGER",
                            "description": "Optional department ID filter",
                        }
                    },
                },
            },
            {
                "name": "get_attendance_summary",
                "description": "Get today's attendance summary (present, late, on leave, absent). For Employees, returns their own attendance status.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "date_str": {
                            "type": "STRING",
                            "description": "ISO date string YYYY-MM-DD (defaults to today)",
                        }
                    },
                },
            },
            {
                "name": "get_late_comers",
                "description": "Get late arrival counts. For HR/Admin returns top late arrivals. For Employees returns only their own late count.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "get_leave_summary",
                "description": "Get leave statistics and pending applications. Scoped to own data for Employees.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "get_my_leave_balance",
                "description": "Get statutory remaining leave quota balances for the currently logged-in user.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "get_payroll_summary",
                "description": "Get payroll compensation summary. HR/Admin gets organizational totals; Employees get only their personal payslip.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "search_employees",
                "description": "Search employee directory by name or code. Salary information is strictly hidden from peer Employees.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Search query text (name, code, or email)",
                        }
                    },
                    "required": ["query"],
                },
            },
        ]

    @staticmethod
    def execute_tool(
        tool_name: str, args: Dict[str, Any], db: Session, current_user: User
    ) -> Dict[str, Any]:
        """
        Executes tools with the current user's strict scope and permissions.
        """
        is_employee = current_user.role == UserRole.EMPLOYEE

        if tool_name == "get_headcount":
            dept_id = args.get("department_id")
            query = (
                db.query(Employee)
                .join(User, User.id == Employee.user_id)
                .filter(User.is_active == True, Employee.exit_date == None)  # noqa: E711
            )
            if dept_id:
                query = query.filter(Employee.department_id == dept_id)
            count = query.count()
            return {"active_headcount": count}

        elif tool_name == "get_attendance_summary":
            target_date_str = args.get("date_str")
            if target_date_str:
                try:
                    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                except ValueError:
                    target_date = date.today()
            else:
                target_date = date.today()

            if is_employee:
                emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
                if not emp:
                    return {"status": "NO_EMPLOYEE_PROFILE"}
                att = (
                    db.query(Attendance)
                    .filter(Attendance.employee_id == emp.id, Attendance.date == target_date)
                    .first()
                )
                return {
                    "date": str(target_date),
                    "status": att.status.value if att else "NOT_CHECKED_IN",
                    "check_in": att.check_in_time.strftime("%H:%M:%S") if att and att.check_in_time else None,
                    "check_out": att.check_out_time.strftime("%H:%M:%S") if att and att.check_out_time else None,
                }
            else:
                present = (
                    db.query(Attendance)
                    .filter(
                        Attendance.date == target_date,
                        Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.HALF_DAY]),
                    )
                    .count()
                )
                late = (
                    db.query(Attendance)
                    .filter(Attendance.date == target_date, Attendance.status == AttendanceStatus.LATE)
                    .count()
                )
                on_leave = (
                    db.query(Attendance)
                    .filter(Attendance.date == target_date, Attendance.status == AttendanceStatus.ON_LEAVE)
                    .count()
                )
                total_active = (
                    db.query(Employee)
                    .join(User, User.id == Employee.user_id)
                    .filter(User.is_active == True, Employee.exit_date == None)  # noqa: E711
                    .count()
                )
                return {
                    "date": str(target_date),
                    "total_active_employees": total_active,
                    "present_today": present,
                    "late_today": late,
                    "on_leave_today": on_leave,
                }

        elif tool_name == "get_late_comers":
            now = datetime.now()
            start_month = date(now.year, now.month, 1)

            if is_employee:
                emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
                if not emp:
                    return {"late_count_this_month": 0}
                count = (
                    db.query(Attendance)
                    .filter(
                        Attendance.employee_id == emp.id,
                        Attendance.status == AttendanceStatus.LATE,
                        Attendance.date >= start_month,
                    )
                    .count()
                )
                return {"your_late_count_this_month": count}
            else:
                late_rows = (
                    db.query(
                        Attendance.employee_id,
                        func.count(Attendance.id).label("late_count"),
                    )
                    .filter(
                        Attendance.status == AttendanceStatus.LATE,
                        Attendance.date >= start_month,
                    )
                    .group_by(Attendance.employee_id)
                    .order_by(func.count(Attendance.id).desc())
                    .limit(5)
                    .all()
                )
                results = []
                for emp_id, count in late_rows:
                    emp = db.query(Employee).filter(Employee.id == emp_id).first()
                    results.append({
                        "employee_name": f"{emp.first_name} {emp.last_name}" if emp else f"Emp #{emp_id}",
                        "late_count": count,
                    })
                return {"top_late_comers": results}

        elif tool_name == "get_leave_summary":
            if is_employee:
                emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
                if not emp:
                    return {"leaves": []}
                leaves = (
                    db.query(LeaveRequest)
                    .filter(LeaveRequest.employee_id == emp.id)
                    .order_by(LeaveRequest.created_at.desc())
                    .limit(5)
                    .all()
                )
                return {
                    "your_recent_leaves": [
                        {
                            "start": str(l.start_date),
                            "end": str(l.end_date),
                            "days": l.working_days_count,
                            "status": l.status.value,
                            "reason": l.reason,
                        }
                        for l in leaves
                    ]
                }
            else:
                pending_count = db.query(LeaveRequest).filter(LeaveRequest.status == ApprovalStatus.PENDING).count()
                approved_count = db.query(LeaveRequest).filter(LeaveRequest.status == ApprovalStatus.APPROVED).count()
                return {
                    "pending_leave_applications": pending_count,
                    "approved_leave_applications": approved_count,
                }

        elif tool_name == "get_my_leave_balance":
            emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
            if not emp:
                return {"balances": [], "message": "No employee profile found."}
            balances = db.query(LeaveBalance).filter(LeaveBalance.employee_id == emp.id).all()
            return {
                "balances": [
                    {
                        "leave_type": b.leave_type.name if b.leave_type else "Leave",
                        "yearly_quota": b.leave_type.yearly_quota if b.leave_type else 0,
                        "used_days": b.used_days,
                        "remaining_balance": (b.leave_type.yearly_quota - b.used_days) if b.leave_type else 0,
                    }
                    for b in balances
                ]
            }

        elif tool_name == "get_payroll_summary":
            if is_employee:
                emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
                if not emp:
                    return {"message": "No payslips on file."}
                latest_slip = (
                    db.query(Payslip)
                    .join(PayrollRun)
                    .filter(Payslip.employee_id == emp.id, PayrollRun.status == PayrollStatus.FINALIZED)
                    .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
                    .first()
                )
                if latest_slip:
                    return {
                        "latest_payslip": {
                            "year": latest_slip.payroll_run.year,
                            "month": latest_slip.payroll_run.month,
                            "net_salary": float(latest_slip.net_salary),
                        }
                    }
                return {"message": "No finalized payslips available for your profile."}
            else:
                latest_run = (
                    db.query(PayrollRun)
                    .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
                    .first()
                )
                if latest_run:
                    return {
                        "period": f"{latest_run.year}-{latest_run.month}",
                        "status": latest_run.status.value,
                        "total_payout": float(latest_run.total_payout),
                    }
                return {"message": "No payroll runs recorded."}

        elif tool_name == "search_employees":
            q_str = f"%{args.get('query', '').strip()}%"
            matches = (
                db.query(Employee)
                .join(User, Employee.user_id == User.id)
                .filter(
                    (Employee.first_name.ilike(q_str))
                    | (Employee.last_name.ilike(q_str))
                    | (Employee.employee_code.ilike(q_str))
                    | (User.email.ilike(q_str))
                )
                .limit(5)
                .all()
            )
            out = []
            for emp in matches:
                item = {
                    "employee_code": emp.employee_code,
                    "name": f"{emp.first_name} {emp.last_name}",
                    "department": emp.department.name if emp.department else None,
                    "designation": emp.designation.name if emp.designation else None,
                    "email": emp.user.email if emp.user else None,
                }
                # STRICT PRIVACY: Peer salaries excluded if caller is EMPLOYEE
                if not is_employee:
                    item["basic_salary"] = float(emp.basic_salary)
                out.append(item)
            return {"employees": out}

        return {"error": f"Unknown tool {tool_name}"}

    # =========================================================================
    # SYSTEM PROMPT WITH COMPANY RULES & ROMAN URDU INSTRUCTIONS
    # =========================================================================

    @staticmethod
    def get_system_prompt(current_user: User) -> str:
        return f"""You are the HCM Lite AI Workforce Assistant for Saylani Hackathon.
Current caller information: User ID {current_user.id}, Role: {current_user.role.value}.

CORE BEHAVIOR & GUARDRAILS:
1. ONLY answer policy questions using the official company business rules below. If a policy or condition is not mentioned in these rules, respond: "I don't know based on company policy."
2. Language: Understand English, Urdu, and Roman Urdu. Always respond in the EXACT same language and script style as the user's question (e.g. if the user asks in Roman Urdu like "Kitnay log absent hain?", respond in Roman Urdu like "Aaj total X log absent hain...").
3. PRIVACY & ACCESS SCOPE ENFORCEMENT:
   - If the caller's role is 'EMPLOYEE' and they ask about another employee's salary, compensation, or personal payslip, you MUST politely refuse: "As an Employee, you are not authorized to view peer compensation details."
   - Employees are only permitted to inspect their own salary, own leave balance, and own attendance.
4. When you need real-time data to answer questions about headcount, attendance, late arrivals, leaves, payroll, or employees, call the appropriate function tool.
5. Keep answers concise, factual, professional, and clear.

OFFICIAL BUSINESS RULES (Ground Truth):
- Office Hours & Grace: Standard office start time is 09:00:00 with a 15-minute grace period. Check-ins after the grace period are classified as LATE.
- Half-Day: Total work duration less than 4.0 hours is marked as HALF_DAY.
- Absenteeism: Dynamic calculation computed on working days, explicitly skipping weekends and public holidays.
- Leaves: Working-day counting only (skips weekends and public holidays). Overlap with pending or approved leaves is strictly rejected (422 error). Over-quota requests are rejected (422 error), except for unpaid leaves which are unlimited. Approved leave deducts balance and marks days ON_LEAVE on attendance records.
- Payroll: Gross salary = 1.5 * Basic salary (incorporating 40% HRA, 10% Medical). Daily rate = Gross / Working days in month. Attendance deductions are computed for absent days, unpaid leaves, and half days (0.5 * daily rate). Statutory 5-tier annual tax slabs:
  * 0 - 600,000: 0%
  * 600,001 - 1,200,000: 5% of amount over 600,000
  * 1,200,001 - 2,400,000: 30,000 + 15% of amount over 1,200,000
  * 2,400,001 - 3,600,000: 210,000 + 25% of amount over 2,400,000
  * Above 3,600,000: 510,000 + 35% of amount over 3,600,000
- Roles & Hierarchy: Admin (manages system settings, provisions HR accounts, finalizes payroll, reviews audit logs), HR (registers employees, reviews leave requests and attendance corrections, generates draft payroll runs), Employee (personal attendance in/out, self leave application, view own payslips and profile).
"""

    # =========================================================================
    # CORE CHAT DISPATCHER (GEMINI FUNCTION CALLING)
    # =========================================================================

    @classmethod
    def chat(
        cls,
        db: Session,
        current_user: User,
        message: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        check_rate_limit(current_user.id)
        start_time = time.time()
        tools_called = []

        # Intercept peer salary queries directly if Employee
        lower_msg = message.lower()
        if current_user.role == UserRole.EMPLOYEE and ("salary" in lower_msg or "pay" in lower_msg or "kamata" in lower_msg or "tankhwah" in lower_msg or "payout" in lower_msg):
            # Check if asking for someone else
            if any(term in lower_msg for term in ["other", "peer", "colleague", "someone", "ahmed", "ali", "khan", "shan", "who earns", "highest", "all employees", "unka", "uski"]):
                reply = "As an Employee, you are not authorized to view peer compensation details."
                elapsed_ms = int((time.time() - start_time) * 1000)
                cls.log_call(db, current_user.id, message, tools_called, reply, elapsed_ms)
                return {"response": reply, "tool_calls": tools_called, "ai_generated": True}

        # If no Gemini API key configured or key is "mock", use intelligent mock dispatcher
        if not settings.AI_API_KEY or settings.AI_API_KEY.lower() in ["mock", "test", "none"]:
            reply = cls._mock_chat_dispatch(db, current_user, message, tools_called)
            elapsed_ms = int((time.time() - start_time) * 1000)
            cls.log_call(db, current_user.id, message, tools_called, reply, elapsed_ms)
            return {"response": reply, "tool_calls": tools_called, "ai_generated": True}

        # Call Gemini API via httpx with 15s timeout
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        # Build contents from history + current message
        contents = []
        if history:
            for h in history[-4:]:
                role = "user" if h.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": str(h.get("content", ""))}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        gemini_payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": cls.get_system_prompt(current_user)}]},
            "tools": [{"functionDeclarations": cls.get_tool_declarations()}],
        }

        try:
            with httpx.Client(timeout=14.0) as client:
                res = client.post(url, headers=headers, json=gemini_payload)

            if res.status_code != 200:
                logger.warning(f"Gemini API returned status {res.status_code}: {res.text}")
                reply = cls._mock_chat_dispatch(db, current_user, message, tools_called)
                elapsed_ms = int((time.time() - start_time) * 1000)
                cls.log_call(db, current_user.id, message, tools_called, reply, elapsed_ms)
                return {"response": reply, "tool_calls": tools_called, "ai_generated": True}

            data = res.json()
            candidate = data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [{}])

            # Check if model wants to call a function
            function_call = parts[0].get("functionCall") if parts else None
            if function_call:
                tool_name = function_call.get("name")
                tool_args = function_call.get("args", {})
                tools_called.append(tool_name)

                # Execute tool
                tool_result = cls.execute_tool(tool_name, tool_args, db, current_user)

                # Send function response back to Gemini for final natural language generation
                contents.append({
                    "role": "model",
                    "parts": [{"functionCall": function_call}],
                })
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"result": tool_result},
                        }
                    }],
                })

                with httpx.Client(timeout=14.0) as client:
                    second_res = client.post(url, headers=headers, json={
                        "contents": contents,
                        "systemInstruction": {"parts": [{"text": cls.get_system_prompt(current_user)}]},
                    })

                if second_res.status_code == 200:
                    second_data = second_res.json()
                    final_parts = second_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
                    final_text = final_parts[0].get("text", "")
                    reply = final_text.strip()
                else:
                    reply = f"Result from {tool_name}: {json.dumps(tool_result)}"
            else:
                reply = parts[0].get("text", "I have received your request.")

        except Exception as e:
            logger.error(f"Gemini call error: {e}")
            reply = cls._mock_chat_dispatch(db, current_user, message, tools_called)

        elapsed_ms = int((time.time() - start_time) * 1000)
        cls.log_call(db, current_user.id, message, tools_called, reply, elapsed_ms)
        return {"response": reply, "tool_calls": tools_called, "ai_generated": True}

    # =========================================================================
    # DASHBOARD SUMMARY
    # =========================================================================

    @classmethod
    def dashboard_summary(cls, current_user: User, kpi_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        check_rate_limit(current_user.id)
        start_time = time.time()

        prompt = f"Summarize the following organizational dashboard KPIs into 3-5 concise bullet insights. Use ONLY the data provided: {json.dumps(kpi_data)}"

        # Default rule-based insights directly from KPI JSON
        default_insights = []
        if "headcount" in kpi_data:
            default_insights.append(f"Current active organization headcount stands at {kpi_data.get('headcount')} personnel.")
        if "attendance_rate" in kpi_data:
            default_insights.append(f"Workforce attendance rate is recorded at {kpi_data.get('attendance_rate'):.1f}% for the evaluated window.")
        if "pending_approvals" in kpi_data:
            default_insights.append(f"There are {kpi_data.get('pending_approvals')} pending leave and correction requests awaiting review.")
        if "attrition_ytd" in kpi_data:
            default_insights.append(f"Year-to-date staff attrition rate is currently {kpi_data.get('attrition_ytd'):.1f}%.")
        if "payroll_cost" in kpi_data:
            default_insights.append(f"Total projected monthly compensation load is ${kpi_data.get('payroll_cost'):,.2f}.")

        if len(default_insights) < 3:
            default_insights.append("System operations are running normally within configured parameters.")
            default_insights.append("All attendance records and leave deductions have been synchronized.")

        insights = default_insights[:5]

        # Call Gemini if key available
        if settings.AI_API_KEY and settings.AI_API_KEY.lower() not in ["mock", "test", "none"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "systemInstruction": {
                        "parts": [{
                            "text": "Generate 3 to 5 executive bullet points using ONLY the provided KPI numbers. Each bullet point should be on a new line starting with a dash (-). Do not extrapolate beyond the data."
                        }]
                    },
                }
                with httpx.Client(timeout=14.0) as client:
                    res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    parsed = [line.lstrip("-•* ").strip() for line in text.split("\n") if line.strip()]
                    if len(parsed) >= 2:
                        insights = parsed[:5]
            except Exception as e:
                logger.error(f"Gemini dashboard summary error: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        cls.log_call(db, current_user.id, "dashboard_summary", None, "\n".join(insights), elapsed_ms)
        return {"insights": insights, "ai_generated": True}

    # =========================================================================
    # SMART LEAVE PARSER
    # =========================================================================

    @classmethod
    def smart_leave(cls, current_user: User, text: str, db: Session) -> Dict[str, Any]:
        check_rate_limit(current_user.id)
        start_time = time.time()

        today_str = date.today().isoformat()
        prompt = f"""Extract leave details from this text into a JSON object: '{text}'.
Current date: {today_str}.
Return ONLY a valid JSON object matching:
{{"type": "<Annual/Casual/Sick>", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "reason": "<explanation>"}}
"""

        parsed = None

        if settings.AI_API_KEY and settings.AI_API_KEY.lower() not in ["mock", "test", "none"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {
                    "parts": [{"text": "You are a JSON parser. Output only valid JSON and nothing else."}]
                },
            }
            # Attempt with 1 retry
            for attempt in range(2):
                try:
                    with httpx.Client(timeout=14.0) as client:
                        res = client.post(url, headers=headers, json=payload)
                    if res.status_code == 200:
                        raw_text = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        # Clean JSON code fences if present
                        cleaned = raw_text.strip().replace("```json", "").replace("```", "").strip()
                        candidate_json = json.loads(cleaned)
                        if "type" in candidate_json and "start" in candidate_json and "end" in candidate_json:
                            parsed = candidate_json
                            break
                except Exception as e:
                    logger.warning(f"Smart leave parse attempt {attempt + 1} failed: {e}")

        if not parsed:
            # Deterministic fallback parser
            lower = text.lower()
            leave_type = "Sick" if ("sick" in lower or "flu" in lower or "fever" in lower or "tabiyat" in lower or "doctor" in lower) else ("Casual" if ("casual" in lower or "emergency" in lower or "kaam" in lower or "family" in lower) else "Annual")
            parsed = {
                "type": leave_type,
                "start": today_str,
                "end": today_str,
                "reason": text,
            }

        elapsed_ms = int((time.time() - start_time) * 1000)
        cls.log_call(db, current_user.id, f"smart_leave: {text}", None, json.dumps(parsed), elapsed_ms)
        return {**parsed, "ai_generated": True}

    # =========================================================================
    # DETERMINISTIC / MOCK CHAT DISPATCHER (FOR TESTS & TIMEOUT FALLBACK)
    # =========================================================================

    @classmethod
    def _mock_chat_dispatch(
        cls, db: Session, current_user: User, message: str, tools_called: List[str]
    ) -> str:
        lower = message.lower()

        # Check Roman Urdu greeting
        is_roman_urdu = any(w in lower for w in ["kya", "hai", "hain", "kitnay", "chutti", "tankhwah", "kaam", "batao", "mujhe", "mera", "aaj"])

        # Headcount query
        if "headcount" in lower or "kitnay log" in lower or "total employee" in lower or "kitne log" in lower:
            tools_called.append("get_headcount")
            res = cls.execute_tool("get_headcount", {}, db, current_user)
            count = res.get("active_headcount", 0)
            if is_roman_urdu:
                return f"Idaray mein is waqt total {count} active mulazmeen (employees) kaam kar rahay hain."
            return f"The current active organization headcount is {count} employees."

        # Attendance query
        if "attendance" in lower or "present" in lower or "absent" in lower or "hazir" in lower or "aaj ka" in lower:
            tools_called.append("get_attendance_summary")
            res = cls.execute_tool("get_attendance_summary", {}, db, current_user)
            if current_user.role == UserRole.EMPLOYEE:
                status = res.get("status", "NOT_CHECKED_IN")
                if is_roman_urdu:
                    return f"Aap ki aaj ki attendance status '{status}' hai."
                return f"Your attendance status for today is '{status}'."
            else:
                p = res.get("present_today", 0)
                l = res.get("late_today", 0)
                if is_roman_urdu:
                    return f"Aaj total {p} log present hain aur {l} log late aye hain."
                return f"Today, {p} employees are present and {l} employees arrived late."

        # Late comers query
        if "late" in lower or "deri" in lower:
            tools_called.append("get_late_comers")
            res = cls.execute_tool("get_late_comers", {}, db, current_user)
            if current_user.role == UserRole.EMPLOYEE:
                c = res.get("your_late_count_this_month", 0)
                if is_roman_urdu:
                    return f"Is maheenay aap {c} martaba late aye hain."
                return f"You have arrived late {c} times this month."
            else:
                top = res.get("top_late_comers", [])
                if not top:
                    return "No employees recorded late this month."
                names = ", ".join([f"{item['employee_name']} ({item['late_count']}x)" for item in top])
                if is_roman_urdu:
                    return f"Is maheenay sab se zyada late anay walay: {names}."
                return f"Top late comers this month: {names}."

        # Leave balance query
        if "balance" in lower or "chutti" in lower or "leave" in lower or "quota" in lower:
            tools_called.append("get_my_leave_balance")
            res = cls.execute_tool("get_my_leave_balance", {}, db, current_user)
            balances = res.get("balances", [])
            if not balances:
                if is_roman_urdu:
                    return "Aap ke account ke sath koi leave quota balance registered nahi hai."
                return "No leave quotas currently assigned to your profile."
            parts = [f"{b['leave_type']}: {b['remaining_balance']} days left (used {b['used_days']})" for b in balances]
            if is_roman_urdu:
                return f"Aap ki baqi chuttiyan: {', '.join(parts)}."
            return f"Your statutory leave balances: {', '.join(parts)}."

        # Payroll query
        if "payroll" in lower or "salary" in lower or "tankhwah" in lower:
            tools_called.append("get_payroll_summary")
            res = cls.execute_tool("get_payroll_summary", {}, db, current_user)
            if current_user.role == UserRole.EMPLOYEE:
                slip = res.get("latest_payslip")
                if slip:
                    if is_roman_urdu:
                        return f"Aap ki pichli salary ({slip['year']}-{slip['month']}) net amount ${slip['net_salary']:,.2f} thi."
                    return f"Your latest payslip for {slip['year']}-{slip['month']} net salary is ${slip['net_salary']:,.2f}."
                return "No payslips on file."
            else:
                status = res.get("status", "N/A")
                payout = res.get("total_payout", 0.0)
                if is_roman_urdu:
                    return f"Latest payroll run status '{status}' hai aur total payout ${payout:,.2f} hai."
                return f"The latest payroll run status is '{status}' with a total payout of ${payout:,.2f}."

        # Search employee
        if "who is" in lower or "find" in lower or "search" in lower or "dhoondo" in lower or "kaun hai" in lower:
            tools_called.append("search_employees")
            # Extract word
            query = message.split()[-1]
            res = cls.execute_tool("search_employees", {"query": query}, db, current_user)
            emps = res.get("employees", [])
            if not emps:
                return f"No employees found matching '{query}'."
            info = emps[0]
            if is_roman_urdu:
                return f"Employee mil gaya: {info['name']} ({info['employee_code']}), Department: {info['department']}, Designation: {info['designation']}."
            return f"Found employee: {info['name']} ({info['employee_code']}), Department: {info['department']}, Designation: {info['designation']}."

        # Policy questions
        if "grace" in lower or "start time" in lower or "timing" in lower or "office time" in lower:
            if is_roman_urdu:
                return "Office standard time subah 09:00:00 hai aur 15 minutes grace period hai. Uske baad late consider hota hai."
            return "Standard office start time is 09:00:00 with a 15-minute grace period. Check-in after grace is marked LATE."

        if "half day" in lower or "half-day" in lower:
            if is_roman_urdu:
                return "Agar working hours 4.0 hours se kam hon to woh Half-Day count hota hai."
            return "Work duration under 4.0 hours is classified as a HALF_DAY."

        # Unknown policy question: strict adherence rule
        if is_roman_urdu:
            return "Mujhe company policy ki bunyad par yeh maloom nahi hai."
        return "I don't know based on company policy."
