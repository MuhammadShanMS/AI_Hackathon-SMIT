from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_db_and_tables, SessionLocal
from app.services.setup_service import SetupService
from app.api.v1.setup import router as setup_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.audit import router as audit_router
from app.api.v1.org import router as org_router
from app.api.v1.employees import router as employees_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.leaves import router as leaves_router
from app.api.v1.payroll import router as payroll_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.comms import router as comms_router
from app.api.v1.csv_endpoints import router as csv_router
from app.api.v1.ai import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables are created
    create_db_and_tables()

    # Optional auto-bootstrap from environment variables
    db = SessionLocal()
    try:
        bootstrapped = SetupService.auto_bootstrap_from_env(db)
        if bootstrapped:
            print("[INFO] System auto-bootstrapped from environment variables.")
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="HCM Lite - Human Capital Management API",
    lifespan=lifespan
)

# Parse allowed CORS origins
raw_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if not raw_origins or "*" in raw_origins:
    allowed_origins = ["*"]
else:
    allowed_origins = raw_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(setup_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(org_router)
app.include_router(employees_router)
app.include_router(attendance_router)
app.include_router(leaves_router)
app.include_router(payroll_router)
app.include_router(dashboard_router)
app.include_router(comms_router)
app.include_router(csv_router)
app.include_router(ai_router)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "operational",
        "docs_url": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
