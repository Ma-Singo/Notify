import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.models.base import UUIDModel


if TYPE_CHECKING:
    from app.models.users import User


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class NotificationEvent(str, enum.Enum):
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_UPDATED = "account_updated"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"
    EMAIL_VERIFIED = "email_verified"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    CUSTOM = "custom"


class NotificationStatus(str, enum.Enum):
    QUEUED = "queued"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    RETRYING = "retrying"


class Notification(UUIDModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    event: Mapped[NotificationEvent] = mapped_column(
        Enum(NotificationEvent), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), nullable=False, default=NotificationStatus.QUEUED
    )
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User | None] = relationship(
        "User", uselist=False, back_populates="notifications"
    )

    def __repr__(self) -> str:
        return f"<Notification: {self.channel}/{self.event} -> {self.recipient}>"
