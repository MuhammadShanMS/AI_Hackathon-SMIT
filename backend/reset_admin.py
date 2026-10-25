"""
reset_admin.py  -  Run from the backend/ folder:
    python reset_admin.py
Sets the admin user to email=admin@saylani.org / AdminSecurePass123!
Creates the admin row and company settings row if either does not exist.
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security import hash_password
from app.models.models import Base, User, UserRole, CompanySettings

EMAIL = "admin@saylani.org"
PASSWORD = "AdminSecurePass123!"
COMPANY = "Saylani Tech"

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)

with Session() as db:
    # Upsert admin
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if admin:
        admin.email = EMAIL
        admin.hashed_password = hash_password(PASSWORD)
        admin.is_active = True
        admin.must_change_password = False
        print("[reset_admin] Updated existing admin ->", EMAIL)
    else:
        admin = User(
            email=EMAIL,
            hashed_password=hash_password(PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=False,
        )
        db.add(admin)
        print("[reset_admin] Created new admin ->", EMAIL)

    # Ensure company settings row exists (required for is_setup to return true)
    comp = db.query(CompanySettings).first()
    if not comp:
        comp = CompanySettings(
            company_name=COMPANY,
            office_start_time="09:00",
            grace_period_minutes=15,
            half_day_hours_threshold=5.0,
            weekend_days="5,6",
            office_radius_meters=100.0,
        )
        db.add(comp)
        print("[reset_admin] Created company settings ->", COMPANY)
    else:
        print("[reset_admin] Company settings already exist ->", comp.company_name)

    # Ensure departments exist
    from app.models.models import Department, Designation
    depts = ["Engineering", "Human Resources", "Finance", "Marketing", "Operations"]
    for d in depts:
        if not db.query(Department).filter(Department.name == d).first():
            db.add(Department(name=d, description=f"{d} Department"))

    # Ensure designations exist
    desigs = ["Software Engineer", "Senior Software Engineer", "HR Officer", "Finance Manager", "Operations Specialist"]
    for des in desigs:
        if not db.query(Designation).filter(Designation.name == des).first():
            db.add(Designation(name=des, description=f"{des} Role"))

    db.commit()
    print("[reset_admin] Done. Final admin email:", EMAIL)
