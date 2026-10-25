from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=5)


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    body: str
    created_by: int
    author_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
