from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    actor_id: Optional[int] = None
    action: str
    entity: str
    entity_id: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
