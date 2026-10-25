# HCM Lite - Intelligent Human Capital Management System

> **Saylani Hackathon Edition**  
> An AI-assisted, role-governed Human Capital Management (HCM) web platform built with FastAPI, PostgreSQL/SQLAlchemy, and React (Vite).

---

## 🌐 Hosted Deployments & Live Demo
- **Frontend URL**: `https://hcm-lite-frontend.onrender.com` *(Placeholder / Configure on Render)*
- **Backend API Docs**: `https://hcm-lite-backend.onrender.com/docs` *(Placeholder / Configure on Render)*

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Python 3.14 + FastAPI
- **Database & ORM**: SQLAlchemy 2.0 (PostgreSQL in production with connection pooling; SQLite supported locally)
- **Security & Auth**: Native `bcrypt` password hashing, `PyJWT` bearer token authentication, server-side RBAC & row-level scope enforcement
- **Reporting**: `ReportLab` enterprise PDF payslip generation
- **Testing**: `pytest`, `httpx` test client suite (30+ comprehensive integration tests)

### Frontend
- **Framework**: React 19 + Vite
- **Routing**: `react-router-dom` v7 with role-guarded route trees
- **HTTP Client**: `axios` with automatic JWT interceptors and global 401 redirection
- **Data Visualization**: `recharts` for dynamic attendance trends, absenteeism, and department payroll breakdowns
- **Design System**: Tailored, modern glassmorphic theme in vanilla CSS (`src/index.css`), responsive from 375px mobile screens to large desktop monitors

### AI Intelligence (Google Gemini)
- **Engine**: Google Gemini API (`gemini-1.5-flash`) with structured function calling
- **Scope Enforcement**: Server-side tool execution scoped to the authenticated caller's identity (Employees cannot query peer salaries; polite refusal)
- **Guardrails**: In-memory rate limiting (20 requests/user/hour), 15s timeout with graceful fallback, immutable `ai_logs` audit trail, bilingual English + Roman Urdu comprehension

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.10+ (Python 3.11, 3.12, 3.13, 3.14 supported)
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a Python virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
# (On Linux/macOS: cp .env.example .env)

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Backend API will be running at `http://localhost:8000` (Interactive Swagger docs: `http://localhost:8000/docs`).

### 2. Frontend Setup

```bash
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment variables
copy .env.example .env
# (On Linux/macOS: cp .env.example .env)

# Start the Vite development server
npm run dev
```
The web application will be accessible at `http://localhost:5173`.

---

## 👤 Creating the First Root Administrator

HCM Lite starts completely empty with zero dummy data. You have two options to provision the initial Admin:

### Option A: The First-Run Setup Wizard (Recommended)
1. Ensure the backend is running.
2. Visit `http://localhost:5173`.
3. If no administrator exists, the system automatically redirects you to `/setup`.
4. Fill in:
   - **Company / Organization Name** (e.g. `Saylani Welfare Trust`)
   - **Admin Email** (e.g. `admin@saylani.org`)
   - **Admin Password** (Min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character)
5. Submit to complete bootstrap. You will be redirected to `/login` to sign in.

### Option B: Auto-Bootstrap via Environment Variables
Set the following variables in `backend/.env` before launching the backend:
```env
COMPANY_NAME=Acme Innovations Corp
ADMIN_EMAIL=admin@organization.com
ADMIN_PASSWORD=AdminSecurePassword123!
```
On startup, the backend automatically initializes the company settings and creates the root Admin account.

---

## 🤖 Configuring the AI Assistant (`AI_API_KEY`)

1. Obtain a Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2. Open `backend/.env` and supply:
```env
AI_API_KEY=AIzaSy...your_gemini_api_key...
AI_MODEL=gemini-1.5-flash
```
3. Restart the backend server. The AI assistant functions automatically across chat queries, dashboard executive summaries, and natural language leave requests.

---

## 🔑 Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Description | Default / Example |
|---|---|---|
| `PROJECT_NAME` | Name of the HCM instance | `HCM Lite` |
| `DATABASE_URL` | SQLAlchemy database connection string | `sqlite:///./hcm_lite.db` or `postgresql://user:pass@host:5432/dbname` |
| `SECRET_KEY` | JWT encryption secret key (32+ chars) | `change-in-production-min-32-chars` |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | `1440` (24 hours) |
| `CORS_ORIGINS` | Permitted CORS origins (comma-separated or `*`) | `*` |
| `COMPANY_NAME` | Optional bootstrap company name | `Saylani Trust` |
| `ADMIN_EMAIL` | Optional bootstrap admin email | `admin@saylani.org` |
| `ADMIN_PASSWORD` | Optional bootstrap admin password | `AdminPass123!` |
| `AI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `AI_MODEL` | Gemini Model identifier | `gemini-1.5-flash` |

### Frontend (`frontend/.env`)
| Variable | Description | Default / Example |
|---|---|---|
| `VITE_API_URL` | Root URL of backend API server | `http://localhost:8000` |

---

## 🧪 Running the Test Suite

```bash
# Navigate to the backend directory
cd backend

# Run the complete test suite
.venv\Scripts\pytest -v

# Run tests by stage:
.venv\Scripts\pytest tests/test_part1.py -v    # Auth & Setup
.venv\Scripts\pytest tests/test_chunk_a.py -v   # Org, Employees, Attendance
.venv\Scripts\pytest tests/test_stage_b.py -v   # Leave & Payroll
.venv\Scripts\pytest tests/test_stage_c.py -v   # Dashboards, Comms & CSV
.venv\Scripts\pytest tests/test_stage_e.py -v   # AI Engine & Guardrails
```

To validate the frontend build:
```bash
cd frontend
npm run build
```

---

## 📋 Feature Completeness Matrix

### What is Completed (Done)
- [x] **Core & Setup**: First-run bootstrap wizard, setup status check, environment bootstrapping
- [x] **Authentication & RBAC**: JWT auth, bcrypt password hashing, forced first-time password rotation (`must_change_password`)
- [x] **Organization Setup**: Departments, designations, statutory leave types with yearly quotas, public holidays, Admin company settings (work hours, grace, radius, lat/lng)
- [x] **User & Login Management**: Admin user directory, toggle activate/deactivate account, temporary password reset forcing rotation
- [x] **Workforce Governance**: Employee directory with server-side search, filtering, and pagination; employee registration returning temporary password once; Employee 360 profile; self-service contact edit; HR salary editing
- [x] **Attendance Engine**: Real-time check-in/out, late evaluation against grace, half-day calculation, dynamic absent calculation skipping weekends and holidays, monthly calendar, daily floor board, correction requests and manager reviews
- [x] **Camera & Location Attendance (Bonus)**: Web/mobile camera attendance with real-time face detection, GPS geolocation capture, and server-side Haversine geofence distance verification
- [x] **Leave Management**: Leave requests skipping non-working days, overlap prevention (422), quota validation (422), cancellation while pending, balance tracking, HR approvals syncing to `ON_LEAVE`
- [x] **Payroll Engine**: HR monthly draft runs (Gross = 1.5 * Basic), attendance deductions (absent days, unpaid leaves, half-days, joiner/leaver proration), late penalty rule (3 lates = 0.5 day), statutory 5-tier annual tax slabs, Admin finalization with locked runs, ReportLab PDF payslip generation
- [x] **AI Assistant (Gemini)**: Scoped tool calling (`get_headcount`, `get_attendance_summary`, `get_late_comers`, `get_leave_summary`, `get_my_leave_balance`, `get_payroll_summary`, `search_employees`), dashboard AI summary bullets, smart leave natural language parsing, Roman Urdu & English comprehension, strict policy Q&A adherence
- [x] **Dashboards & Comms**: Server-side aggregation for HR, Admin, and Employee; broadcast announcements board; notifications dropdown with real-time unread badges; dry-run CSV employee import/export
- [x] **Frontend SPA & PWA (Bonus)**: React 19 + Vite responsive web application with custom glassmorphic design system (from 375px mobile to 4K displays), role-based routes, PWA web app manifest, and loading/empty/error states
- [x] **Deployment Config**: `render.yaml`, `Procfile`, PostgreSQL URI compatibility, environment templates

### Optional / Future Enhancements (Not in Scope)
- [ ] Hardware biometric physical thumbprint device USB driver (simulated via Web camera & API)
- [ ] Multi-tenant isolation for distinct enterprises under a single DB instance
