import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.models import AuditLog, User


class AuditService:
    @staticmethod
    def _to_json_str(data: Any) -> Optional[str]:
        if data is None:
            return None
        if isinstance(data, str):
            return data
        try:
            return json.dumps(data, default=str)
        except Exception:
            return str(data)

    @staticmethod
    def log(
        db: Session,
        actor: Optional[User],
        action: str,
        entity: str,
        entity_id: Optional[str | int] = None,
        before: Optional[Any] = None,
        after: Optional[Any] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        actor_id = actor.id if actor else None
        log_entry = AuditLog(
            actor_id=actor_id,
            action=action.upper(),
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            before_state=AuditService._to_json_str(before),
            after_state=AuditService._to_json_str(after),
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_logs(db: Session, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        return (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .offset(offset)
            .limit(min(limit, 500))
            .all()
        )
