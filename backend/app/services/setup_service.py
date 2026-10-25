from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.models.models import CompanySettings, User, UserRole, LeaveType, Department, Designation
from app.services.audit_service import AuditService


class SetupService:
    @staticmethod
    def is_setup_completed(db: Session) -> bool:
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first() is not None
        company_exists = db.query(CompanySettings).first() is not None
        return admin_exists and company_exists

    @staticmethod
    def get_company_name(db: Session) -> Optional[str]:
        comp = db.query(CompanySettings).first()
        return comp.company_name if comp else None

    @staticmethod
    def perform_setup(
        db: Session,
        company_name: str,
        admin_email: str,
        admin_password: str,
        ip_address: Optional[str] = None
    ) -> dict:
        # Already fully set up: both admin AND company settings exist
        if SetupService.is_setup_completed(db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup has already been completed for this installation."
            )

        # 1. Company Settings
        comp_settings = db.query(CompanySettings).first()
        if not comp_settings:
            comp_settings = CompanySettings(
                company_name=company_name.strip(),
                office_start_time="09:00",
                grace_period_minutes=15,
                half_day_hours_threshold=5.0,
                weekend_days="5,6",
                office_radius_meters=100.0
            )
            db.add(comp_settings)
        else:
            comp_settings.company_name = company_name.strip()

        # 2. Seed Default Leave Types if not existing
        default_leave_types = [
            {"name": "ANNUAL", "yearly_quota": 14, "is_paid": True},
            {"name": "SICK", "yearly_quota": 8, "is_paid": True},
            {"name": "CASUAL", "yearly_quota": 10, "is_paid": True},
            {"name": "UNPAID", "yearly_quota": 0, "is_paid": False},
        ]
        for lt_data in default_leave_types:
            existing_lt = db.query(LeaveType).filter(LeaveType.name == lt_data["name"]).first()
            if not existing_lt:
                db.add(LeaveType(**lt_data))

        # 3. Create or update Admin User
        admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin_user:
            # Admin already exists (e.g. created by reset_admin.py) – just update credentials
            admin_user.email = admin_email.strip().lower()
            admin_user.hashed_password = hash_password(admin_password)
            admin_user.is_active = True
            admin_user.must_change_password = False
        else:
            admin_user = User(
                email=admin_email.strip().lower(),
                hashed_password=hash_password(admin_password),
                role=UserRole.ADMIN,
                is_active=True,
                must_change_password=False
            )
            db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # 4. Audit Log
        AuditService.log(
            db=db,
            actor=admin_user,
            action="SETUP",
            entity="CompanySettings",
            entity_id=comp_settings.id,
            after={
                "company_name": comp_settings.company_name,
                "admin_email": admin_user.email
            },
            ip_address=ip_address
        )

        return {
            "message": "System setup successfully completed.",
            "company_name": comp_settings.company_name,
            "admin_email": admin_user.email
        }

    @staticmethod
    def auto_bootstrap_from_env(db: Session) -> bool:
        if SetupService.is_setup_completed(db):
            return False

        if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
            company = settings.COMPANY_NAME or "HCM Lite"
            SetupService.perform_setup(
                db=db,
                company_name=company,
                admin_email=settings.ADMIN_EMAIL,
                admin_password=settings.ADMIN_PASSWORD,
                ip_address="127.0.0.1 (bootstrap)"
            )
            return True
        return False
