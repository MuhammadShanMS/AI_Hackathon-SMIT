# HCM Lite - Implementation Progress

## Completed (Done)

### Part 1: Core Foundation & Security
- [x] Project architecture (`routes` -> `services` -> `models` with Pydantic validation)
- [x] Database configuration with SQLAlchemy & SQLite/PostgreSQL support (`Base.metadata.create_all`, no Alembic)
- [x] Security suite: native `bcrypt` password hashing and `PyJWT` access token issuance
- [x] Full relational schema across all required domains
- [x] First-run setup (`GET /setup/status`, `POST /setup`, environment auto-bootstrap)
- [x] Authentication & Authorization (`/auth/login`, `/auth/change-password`, `/auth/me`)
- [x] Security policy enforcement: `must_change_password=True` lockdown until rotated
- [x] Server-side RBAC & row-level scope dependencies (`deps.py`)
- [x] Admin lifecycle: HR provisioning, user activation toggle, temp password resets
- [x] Immutable audit trail (`AuditService.log` and read-only `GET /audit`)

### Chunk A: Org Setup + Employees + Attendance
- [x] **Org Setup**: Admin CRUD & HR view-only for Company Settings, Departments, Designations, Leave Types, and Public Holidays (`/org/*`)
- [x] **Employees Registration**: HR registers employee (`POST /employees`), provisions login with temporary password, sets `must_change_password=True`, auto-creates yearly leave balances from leave types
- [x] **Employee Directory**: Server-side search, filtering (department, status), and pagination; masks salary info from employee peers
- [x] **Employee 360 Profile**: Full profile read-only to self for employees (403 for other employees), editable only for phone & address; HR editable
- [x] **Salary Governance**: Salary structure editable by HR only; Admin view only; Employee cannot see others' salary
- [x] **Attendance Engine**:
  - `POST /attendance/check-in`: server stamped, duplicate on same day returns `409 Conflict`, late status evaluated against start + grace
  - `POST /attendance/check-out`: server stamped, marks `HALF_DAY` if duration under threshold hours
  - Dynamic `ABSENT` calculation: computed on working days skipping weekends and public holidays without storing redundant rows
  - Monthly attendance calendar (`GET /attendance/calendar`) with role-based scoping
  - Daily attendance board (`GET /attendance/daily-board`) for HR & Admin
- [x] **Attendance Corrections**:
  - Employee requests correction with reason (`POST /attendance/corrections`)
  - HR review workflow (`PATCH /attendance/corrections/{id}/review`)
  - Updates underlying attendance record on approval & triggers in-app employee notification

### Stage B: Leave + Payroll
- [x] **Leave Management**:
  - Application with working-day counting (skipping weekends & holidays)
  - Overlap with PENDING/APPROVED leaves returns 422
  - Over-balance returns 422 (unpaid is unlimited)
  - Cancellation allowed while PENDING
  - Balance inspection endpoint (`/leaves/balances`)
  - HR review workflow with balance deduction, attendance syncing to `ON_LEAVE`, and in-app notifications
- [x] **Payroll Engine**:
  - HR monthly DRAFT creation with formulaic compensation (Gross = 1.5 * Basic, HRA 40%, Medical 10%)
  - Daily rate = Gross / Working days in month
  - Deductions for absent days, unpaid leave days, 0.5 * half days, and joiner/leaver prorating
  - 5-tier statutory annual income tax slab computation (0-600k: 0%, 5% to 1.2M, 30k+15% to 2.4M, 210k+25% to 3.6M, 510k+35% above)
  - Admin finalization with locked state preventing further edits
  - Official Payslip PDF generation with reportlab, restricted to employee self-download or HR/Admin access
  - In-app notification on payroll finalization

### Stage C: Dashboards + Comms + CSV
- [x] **Server-side Aggregation Dashboards**:
  - HR Dashboard: headcount, present today, on leave, late today, pending approvals (corrections + leaves), attendance rate, absenteeism by dept, leave by type, top 5 late-comers, 14-day attendance trend. Filterable by date range and department.
  - Admin Dashboard: headcount, attrition YTD, payroll cost, average salary, headcount by dept, payroll cost by dept, gender and tenure breakdown, last 10 audit logs. Filterable by department.
  - Employee Dashboard (own data only): weekly working hours vs 40h standard, late arrivals count, leave balances breakdown, latest payslip snapshot, recent announcements.
- [x] **Comms System**:
  - Announcements: Admin and HR post, accessible by all employees.
  - Notifications: User-targeted notification stream, unread count tracking, single and bulk mark-as-read.
- [x] **CSV Management**:
  - HR employee export with role/department/designation details.
  - HR employee import with dry-run mode returning validation errors per row and field (required fields, unique employee_code/email, valid email, department matching, ISO date, salary > 0).

### Stage D: Frontend Single Page Application (`/frontend`)
- [x] **Vite + React SPA Architecture**:
  - `axios` API client with JWT interceptor and global 401 redirect handling
  - `AuthContext` with boot setup-detection (`/setup/status`) and temporary password change enforcement (`must_change_password`)
  - Role-based protected routes (`ProtectedRoute`) and responsive sidebar navigation (`Layout`)
- [x] **Views & Pages**:
  - `Setup`: Initial company setup & root Admin account creation
  - `Login` & `FirstTimePassword`: Secure credentials login & forced password rotation
  - `Settings`: Admin company parameters (working hours, grace period, radius, lat/lng)
  - `OrgSetup`: Departments, designations, leave types with quotas, public holidays, and HR login provisioning
  - `Employees`: Directory with search/filters/paging, employee registration modal with one-time temporary password display, Employee 360 profile drawer, self-edit, and dry-run CSV import/export
  - `Attendance`: Check-in/out buttons, monthly attendance calendar, daily attendance floor board, correction request & HR approval modal
  - `Leaves`: Quota balance cards, application modal, Smart Leave NLP box, history table, and HR review inbox
  - `Payroll`: HR draft generation, Admin finalization with locked badge, and itemized payslip PDF download
  - `Dashboard`: Role-tailored dashboards (HR, Admin, Employee) with KPI metric cards, Recharts visualizations, and department/date filters
  - `Announcements`: Notice board with creation form for HR/Admin
  - `Notifications`: Real-time bell dropdown with unread count and mark-as-read
  - `AuditLogs`: Forensic search and audit trail viewer for Admin
- [x] **Design System & AI Integration**:
  - Custom glassmorphic design system in `src/index.css` with responsive layout from 375px
  - Global `AiChatDrawer` component on all pages with "AI-generated" response badge
  - "Summarize with AI" button on dashboards
  - `frontend/.env.example` created with `VITE_API_URL`

### Stage F: Deployment Preparation
- [x] **PostgreSQL & Database Setup**:
  - `DATABASE_URL` automatic conversion from `postgres://` to `postgresql://`
  - Connection pooling with `pool_pre_ping=True` for production PostgreSQL instances
  - Tables auto-created on startup with `Base.metadata.create_all`
- [x] **CORS & Environment Governance**:
  - Dynamic `CORS_ORIGINS` parsing from env
  - Root `.gitignore` and `backend/.gitignore` properly ignoring `.env`, databases, virtual environments, and dist folders
  - Comprehensive `.env.example` templates for root, backend, and frontend
- [x] **Hosting Infrastructure**:
  - `render.yaml` defining full-stack blueprint: PostgreSQL database, Python FastAPI web service, and Vite React static site
  - `Procfile` configured for backend process execution (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
- [x] **Documentation**:
  - Complete `README.md` covering architecture, local development, first-run admin creation, Gemini AI configuration, environment variables reference, test commands, and feature matrix

---

## Pending (Next Stages)
- [ ] **Stage E**: AI Assistant (Gemini API tool calling, policy Q&A, rate limits, smart leave parsing, frontend integration)

---

## Decisions
1. **Designation Model**: Standalone organization-wide catalog linked via foreign keys to `employees`.
2. **Absent Calculation**: Computed dynamically during monthly calendar and daily board generation; skipped on holidays and weekends.
3. **Leave Calendar Sync**: Approved leave automatically sets attendance status to `ON_LEAVE` for working days within the leave window and prevents false `MISSING_CHECKOUT` flags.
4. **Payroll Tax Bracket**: Calculated on annual projected gross (`gross * 12`), divided by 12 for the monthly deduction.
5. **ReportLab Payslip Generation**: Clean tabular document layout with distinct earnings and deductions breakdown, company header, and formal certification note.
6. **Attendance & Absenteeism Formulas**:
   - Attendance rate = `(present + late + missing_checkout + 0.5 * half_day) / (working_day_records - on_leave) * 100`
   - Late % = `late / (present + late) * 100`
   - Absenteeism % = `absent_days / expected_working_days * 100`
   - Leave utilization % = `approved_days / quota * 100`
   - Attrition % = `exits / average_headcount * 100`
7. **CSV Import User Provisioning**: Successfully imported rows in non-dry-run mode automatically generate employee records and user logins with temporary passwords.
8. **Frontend UI Architecture**: Built using Vite + React + Lucide Icons + Recharts with a custom CSS design system rather than heavy CSS frameworks for ultra-fast bundle delivery, clean glassmorphism styling, and mobile responsiveness down to 375px.
9. **Deployment Strategy**: Infrastructure blueprint provided via `render.yaml` with zero-config database binding and SPA routing rewrites.



