# HCM Lite - Intelligent Human Capital Management System

> **Saylani Hackathon Edition**  
> An AI-assisted, role-governed Human Capital Management (HCM) web platform built with FastAPI, PostgreSQL/SQLAlchemy, and React (Vite).

---

## 🌐 Hosted Deployments & Live Demo
- **Live frontend**: TBD
- **Live backend**: TBD

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Python 3.10+ / FastAPI
- **Database & ORM**: SQLAlchemy 2.0 (PostgreSQL in production; SQLite supported locally)
- **Security & Auth**: Native `bcrypt` password hashing, `PyJWT` bearer token authentication, server-side RBAC & row-level scope enforcement
- **Reporting**: `ReportLab` enterprise PDF payslip generation
- **Testing**: `pytest`, `httpx` test client suite (41 comprehensive integration tests)

### Frontend
- **Framework**: React 19 + Vite
- **Routing**: `react-router-dom` v7 with role-guarded route trees and SPA rewrites
- **HTTP Client**: `axios` with automatic JWT interceptors and global 401 redirection
- **Data Visualization**: `recharts` for dynamic attendance trends, absenteeism, and department payroll breakdowns
- **Design System**: Tailored, modern glassmorphic theme in vanilla CSS (`src/index.css`), responsive from 375px mobile screens to large desktop displays
- **Computer Vision**: `face-api.js` (TinyFaceDetector) running locally from `/models` for real-time camera face verification

### AI Intelligence (Google Gemini)
- **Engine**: Google Gemini API (`gemini-1.5-flash`) with structured function calling
- **Scope Enforcement**: Server-side tool execution scoped to the authenticated caller's identity (Employees cannot query peer salaries; polite refusal)
- **Guardrails**: In-memory rate limiting (20 requests/user/hour), 15s timeout with graceful fallback, immutable `ai_logs` audit trail, bilingual English + Roman Urdu comprehension

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.10+ (Python 3.10, 3.11, 3.12, 3.13, 3.14 supported)
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

## 👤 First-Run Admin Setup

HCM Lite starts with zero dummy data so judges experience a genuine first-run setup:

### The First-Run Setup Wizard
1. Open the application in your browser (locally at `http://localhost:5173` or at the live frontend URL).
2. Because no administrator exists yet, the system automatically redirects you to `/setup`.
3. Fill in:
   - **Company / Organization Name** (e.g., `Saylani Tech Solutions`)
   - **Admin Email** (e.g., `admin@company.org`)
   - **Admin Password** (Min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character)
4. Submit the form to complete initialization. You will be redirected to `/login` to sign in as Admin.

### Optional Headless Bootstrap via Environment Variables
If preferred for containerized environments, setting `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the backend environment variables will automatically initialize the Admin account upon startup. If left unset, the web setup wizard at `/setup` is shown.

---

## 🔑 Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Required | Description |
|---|---|---|
| `PROJECT_NAME` | Optional | Application instance title |
| `DATABASE_URL` | Yes | Database connection string (PostgreSQL or SQLite) |
| `SECRET_KEY` | Yes | Cryptographic secret for signing JWT tokens (min 32 chars) |
| `ALGORITHM` | Optional | JWT algorithm (defaults to `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | JWT token lifespan in minutes |
| `CORS_ORIGINS` | Optional | Allowed CORS origins (comma-separated domains or `*`) |
| `COMPANY_NAME` | Optional | Auto-bootstrap company name (leave unset for web setup wizard) |
| `ADMIN_EMAIL` | Optional | Auto-bootstrap admin email (leave unset for web setup wizard) |
| `ADMIN_PASSWORD` | Optional | Auto-bootstrap admin password (leave unset for web setup wizard) |
| `AI_API_KEY` | Optional | Google Gemini API Key for AI features |
| `AI_MODEL` | Optional | Model identifier (defaults to `gemini-1.5-flash`) |

### Frontend (`frontend/.env`)
| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Yes | Backend API base URL (e.g. `https://your-backend.onrender.com`) |

---

## 🧪 Testing and Verification

To execute the backend test suite:
```bash
cd backend
.venv\Scripts\python -m pytest
```
*Result: 41 passed, 0 failed.*

To build the frontend production assets:
```bash
cd frontend
npm run build
```
*Result: Exit code 0, optimized bundle with zero build errors.*

---

## 📋 Feature Completeness Matrix

### Done
- [x] **Core & First-Run Setup**: Initial wizard `/setup`, setup status check `/setup/status`, auto-creation of tables on startup
- [x] **Authentication & RBAC**: JWT auth, bcrypt hashing, mandatory first-time password rotation (`must_change_password`)
- [x] **Organization Setup**: Departments, designations, statutory leave types with yearly quotas, public holidays, Admin company settings (work hours, grace period, radius, lat/lng)
- [x] **User & Login Management**: Admin user directory, toggle activate/deactivate account, temporary password reset forcing first-login change
- [x] **Workforce Governance**: Employee directory with server-side search, filtering, and pagination; employee registration returning temporary password once; Employee 360 profile; self-service contact edit; HR salary editing
- [x] **Attendance Engine**: Real-time check-in/out, late evaluation against grace, half-day calculation, dynamic absent calculation skipping weekends and holidays, monthly calendar, daily floor board, correction requests and manager reviews
- [x] **Camera & Location Attendance (Bonus)**: Web/mobile camera attendance with real-time face detection (using local models in `/models`), GPS geolocation capture, and server-side Haversine geofence distance verification
- [x] **Leave Management**: Leave requests skipping non-working days, overlap prevention (422), quota validation (422), cancellation while pending, balance tracking, HR approvals syncing to `ON_LEAVE`
- [x] **Payroll Engine**: HR monthly draft runs (Gross = 1.5 * Basic), attendance deductions (absent days, unpaid leaves, half-days, joiner/leaver proration), late penalty rule (3 lates = 0.5 day), statutory 5-tier annual tax slabs, Admin finalization with locked runs, ReportLab PDF payslip generation
- [x] **AI Assistant (Gemini)**: Scoped tool calling (`get_headcount`, `get_attendance_summary`, `get_late_comers`, `get_leave_summary`, `get_my_leave_balance`, `get_payroll_summary`, `search_employees`), dashboard AI summary bullets, smart leave natural language parsing, Roman Urdu & English comprehension, strict policy Q&A adherence
- [x] **Dashboards & Comms**: Server-side aggregation for HR, Admin, and Employee; broadcast announcements board; notifications dropdown with real-time unread badges; dry-run CSV employee import/export
- [x] **Frontend SPA & PWA (Bonus)**: React 19 + Vite responsive web application with custom glassmorphic design system (from 375px mobile to 4K displays), role-based routes, PWA web app manifest, and loading/empty/error states
- [x] **Deployment Config**: `render.yaml`, `Procfile`, `frontend/vercel.json` SPA rewrites, PostgreSQL URI compatibility (`postgres://` -> `postgresql://`)

### Not Done / Future Enhancements
- [ ] Hardware biometric physical thumbprint device USB driver (simulated via Web camera & API)
- [ ] Multi-tenant isolation for distinct enterprises under a single DB instance
