from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import CompanySettings, Department, Designation, LeaveType, Holiday, Employee, User
from app.schemas.org import (
    CompanySettingsUpdate, DepartmentCreate, DepartmentUpdate,
    DesignationCreate, DesignationUpdate, LeaveTypeCreate, LeaveTypeUpdate,
    HolidayCreate, HolidayUpdate
)
from app.services.audit_service import AuditService


class OrgService:
    # --- Company Settings ---
    @staticmethod
    def get_settings(db: Session) -> CompanySettings:
        settings = db.query(CompanySettings).first()
        if not settings:
            settings = CompanySettings(
                company_name="HCM Lite",
                office_start_time="09:00",
                grace_period_minutes=15,
                half_day_hours_threshold=5.0,
                weekend_days="5,6",
                office_radius_meters=100.0
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    def update_settings(
        db: Session,
        actor: User,
        data: CompanySettingsUpdate,
        ip_address: Optional[str] = None
    ) -> CompanySettings:
        settings = OrgService.get_settings(db)
        before_state = {
            "company_name": settings.company_name,
            "office_start_time": settings.office_start_time,
            "grace_period_minutes": settings.grace_period_minutes,
            "half_day_hours_threshold": settings.half_day_hours_threshold,
            "weekend_days": settings.weekend_days,
            "office_latitude": settings.office_latitude,
            "office_longitude": settings.office_longitude,
            "office_radius_meters": settings.office_radius_meters,
        }

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(settings, key, value)

        db.commit()
        db.refresh(settings)

        AuditService.log(
            db=db,
            actor=actor,
            action="UPDATE_SETTINGS",
            entity="CompanySettings",
            entity_id=settings.id,
            before=before_state,
            after=update_dict,
            ip_address=ip_address
        )
        return settings

    # --- Departments ---
    @staticmethod
    def list_departments(db: Session) -> list[Department]:
        return db.query(Department).order_by(Department.name.asc()).all()

    @staticmethod
    def create_department(
        db: Session,
        actor: User,
        data: DepartmentCreate,
        ip_address: Optional[str] = None
    ) -> Department:
        clean_name = data.name.strip()
        existing = db.query(Department).filter(Department.name.ilike(clean_name)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department '{clean_name}' already exists."
            )
        dept = Department(name=clean_name, description=data.description)
        db.add(dept)
        db.commit()
        db.refresh(dept)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_DEPARTMENT",
            entity="Department",
            entity_id=dept.id,
            after={"name": dept.name, "description": dept.description},
            ip_address=ip_address
        )
        return dept

    @staticmethod
    def update_department(
        db: Session,
        actor: User,
        dept_id: int,
        data: DepartmentUpdate,
        ip_address: Optional[str] = None
    ) -> Department:
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found.")

        before_state = {"name": dept.name, "description": dept.description}
        if data.name is not None:
            clean_name = data.name.strip()
            existing = db.query(Department).filter(Department.name.ilike(clean_name), Department.id != dept_id).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Department '{clean_name}' already exists.")
            dept.name = clean_name
        if data.description is not None:
            dept.description = data.description

        db.commit()
        db.refresh(dept)

        AuditService.log(
            db=db,
            actor=actor,
            action="UPDATE_DEPARTMENT",
            entity="Department",
            entity_id=dept.id,
            before=before_state,
            after={"name": dept.name, "description": dept.description},
            ip_address=ip_address
        )
        return dept

    @staticmethod
    def delete_department(
        db: Session,
        actor: User,
        dept_id: int,
        ip_address: Optional[str] = None
    ) -> dict:
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found.")

        emp_count = db.query(Employee).filter(Employee.department_id == dept_id).count()
        if emp_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete department with {emp_count} assigned employees."
            )

        before_state = {"name": dept.name}
        db.delete(dept)
        db.commit()

        AuditService.log(
            db=db,
            actor=actor,
            action="DELETE_DEPARTMENT",
            entity="Department",
            entity_id=dept_id,
            before=before_state,
            ip_address=ip_address
        )
        return {"message": "Department deleted successfully."}

    # --- Designations ---
    @staticmethod
    def list_designations(db: Session) -> list[Designation]:
        return db.query(Designation).order_by(Designation.name.asc()).all()

    @staticmethod
    def create_designation(
        db: Session,
        actor: User,
        data: DesignationCreate,
        ip_address: Optional[str] = None
    ) -> Designation:
        clean_name = data.name.strip()
        existing = db.query(Designation).filter(Designation.name.ilike(clean_name)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Designation '{clean_name}' already exists."
            )
        desig = Designation(name=clean_name, description=data.description)
        db.add(desig)
        db.commit()
        db.refresh(desig)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_DESIGNATION",
            entity="Designation",
            entity_id=desig.id,
            after={"name": desig.name, "description": desig.description},
            ip_address=ip_address
        )
        return desig

    @staticmethod
    def update_designation(
        db: Session,
        actor: User,
        desig_id: int,
        data: DesignationUpdate,
        ip_address: Optional[str] = None
    ) -> Designation:
        desig = db.query(Designation).filter(Designation.id == desig_id).first()
        if not desig:
            raise HTTPException(status_code=404, detail="Designation not found.")

        before_state = {"name": desig.name, "description": desig.description}
        if data.name is not None:
            clean_name = data.name.strip()
            existing = db.query(Designation).filter(Designation.name.ilike(clean_name), Designation.id != desig_id).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Designation '{clean_name}' already exists.")
            desig.name = clean_name
        if data.description is not None:
            desig.description = data.description

        db.commit()
        db.refresh(desig)

        AuditService.log(
            db=db,
            actor=actor,
            action="UPDATE_DESIGNATION",
            entity="Designation",
            entity_id=desig.id,
            before=before_state,
            after={"name": desig.name, "description": desig.description},
            ip_address=ip_address
        )
        return desig

    @staticmethod
    def delete_designation(
        db: Session,
        actor: User,
        desig_id: int,
        ip_address: Optional[str] = None
    ) -> dict:
        desig = db.query(Designation).filter(Designation.id == desig_id).first()
        if not desig:
            raise HTTPException(status_code=404, detail="Designation not found.")

        emp_count = db.query(Employee).filter(Employee.designation_id == desig_id).count()
        if emp_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete designation with {emp_count} assigned employees."
            )

        before_state = {"name": desig.name}
        db.delete(desig)
        db.commit()

        AuditService.log(
            db=db,
            actor=actor,
            action="DELETE_DESIGNATION",
            entity="Designation",
            entity_id=desig_id,
            before=before_state,
            ip_address=ip_address
        )
        return {"message": "Designation deleted successfully."}

    # --- Leave Types ---
    @staticmethod
    def list_leave_types(db: Session) -> list[LeaveType]:
        return db.query(LeaveType).order_by(LeaveType.id.asc()).all()

    @staticmethod
    def create_leave_type(
        db: Session,
        actor: User,
        data: LeaveTypeCreate,
        ip_address: Optional[str] = None
    ) -> LeaveType:
        clean_name = data.name.strip().upper()
        existing = db.query(LeaveType).filter(LeaveType.name == clean_name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave type '{clean_name}' already exists."
            )
        lt = LeaveType(name=clean_name, yearly_quota=data.yearly_quota, is_paid=data.is_paid)
        db.add(lt)
        db.commit()
        db.refresh(lt)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_LEAVE_TYPE",
            entity="LeaveType",
            entity_id=lt.id,
            after={"name": lt.name, "yearly_quota": lt.yearly_quota, "is_paid": lt.is_paid},
            ip_address=ip_address
        )
        return lt

    @staticmethod
    def update_leave_type(
        db: Session,
        actor: User,
        lt_id: int,
        data: LeaveTypeUpdate,
        ip_address: Optional[str] = None
    ) -> LeaveType:
        lt = db.query(LeaveType).filter(LeaveType.id == lt_id).first()
        if not lt:
            raise HTTPException(status_code=404, detail="Leave type not found.")

        before_state = {"name": lt.name, "yearly_quota": lt.yearly_quota, "is_paid": lt.is_paid}
        if data.name is not None:
            clean_name = data.name.strip().upper()
            existing = db.query(LeaveType).filter(LeaveType.name == clean_name, LeaveType.id != lt_id).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Leave type '{clean_name}' already exists.")
            lt.name = clean_name
        if data.yearly_quota is not None:
            lt.yearly_quota = data.yearly_quota
        if data.is_paid is not None:
            lt.is_paid = data.is_paid

        db.commit()
        db.refresh(lt)

        AuditService.log(
            db=db,
            actor=actor,
            action="UPDATE_LEAVE_TYPE",
            entity="LeaveType",
            entity_id=lt.id,
            before=before_state,
            after={"name": lt.name, "yearly_quota": lt.yearly_quota, "is_paid": lt.is_paid},
            ip_address=ip_address
        )
        return lt

    @staticmethod
    def delete_leave_type(
        db: Session,
        actor: User,
        lt_id: int,
        ip_address: Optional[str] = None
    ) -> dict:
        lt = db.query(LeaveType).filter(LeaveType.id == lt_id).first()
        if not lt:
            raise HTTPException(status_code=404, detail="Leave type not found.")

        before_state = {"name": lt.name}
        db.delete(lt)
        db.commit()

        AuditService.log(
            db=db,
            actor=actor,
            action="DELETE_LEAVE_TYPE",
            entity="LeaveType",
            entity_id=lt_id,
            before=before_state,
            ip_address=ip_address
        )
        return {"message": "Leave type deleted successfully."}

    # --- Holidays ---
    @staticmethod
    def list_holidays(db: Session) -> list[Holiday]:
        return db.query(Holiday).order_by(Holiday.date.asc()).all()

    @staticmethod
    def create_holiday(
        db: Session,
        actor: User,
        data: HolidayCreate,
        ip_address: Optional[str] = None
    ) -> Holiday:
        existing = db.query(Holiday).filter(Holiday.date == data.date).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A holiday on date '{data.date}' already exists ('{existing.name}')."
            )
        h = Holiday(date=data.date, name=data.name.strip())
        db.add(h)
        db.commit()
        db.refresh(h)

        AuditService.log(
            db=db,
            actor=actor,
            action="CREATE_HOLIDAY",
            entity="Holiday",
            entity_id=h.id,
            after={"date": str(h.date), "name": h.name},
            ip_address=ip_address
        )
        return h

    @staticmethod
    def update_holiday(
        db: Session,
        actor: User,
        h_id: int,
        data: HolidayUpdate,
        ip_address: Optional[str] = None
    ) -> Holiday:
        h = db.query(Holiday).filter(Holiday.id == h_id).first()
        if not h:
            raise HTTPException(status_code=404, detail="Holiday not found.")

        before_state = {"date": str(h.date), "name": h.name}
        if data.date is not None:
            existing = db.query(Holiday).filter(Holiday.date == data.date, Holiday.id != h_id).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"A holiday already exists on {data.date}.")
            h.date = data.date
        if data.name is not None:
            h.name = data.name.strip()

        db.commit()
        db.refresh(h)

        AuditService.log(
            db=db,
            actor=actor,
            action="UPDATE_HOLIDAY",
            entity="Holiday",
            entity_id=h.id,
            before=before_state,
            after={"date": str(h.date), "name": h.name},
            ip_address=ip_address
        )
        return h

    @staticmethod
    def delete_holiday(
        db: Session,
        actor: User,
        h_id: int,
        ip_address: Optional[str] = None
    ) -> dict:
        h = db.query(Holiday).filter(Holiday.id == h_id).first()
        if not h:
            raise HTTPException(status_code=404, detail="Holiday not found.")

        before_state = {"date": str(h.date), "name": h.name}
        db.delete(h)
        db.commit()

        AuditService.log(
            db=db,
            actor=actor,
            action="DELETE_HOLIDAY",
            entity="Holiday",
            entity_id=h_id,
            before=before_state,
            ip_address=ip_address
        )
        return {"message": "Holiday deleted successfully."}
