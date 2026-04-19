import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.notifications import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    channel: NotificationChannel
    event: NotificationEvent
    status: NotificationStatus
    recipient: str
    subject: str | None
    body: str | None
    celery_task_id: str | None
    error_body: str | None
    retry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SendEmailRequest(BaseModel):
    """Custom email trigger"""

    to: EmailStr
    subject: str = Field(max_length=255)
    body: str
    user_id: uuid.UUID | None = None


class SendSMSRequest(BaseModel):
    """Custom sms trigger"""

    to: str = Field(description="E.164 phone number, e.g. +15551234567")
    body: str = Field(max_length=150)
    user_id: uuid.UUID | None = None


class NotificationPage(BaseModel):
    """Custom notification trigger"""

    items: list[NotificationRead]
    total: int
    page: int
    size: int
    pages: int
