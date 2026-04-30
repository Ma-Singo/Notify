import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.models.base import UUIDModel

if TYPE_CHECKING:
    from app.models.users import User


class PlanInterval(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    PAUSED = "paused"


class Plan(UUIDModel):
    """Billing Plan (synced with Stripe products"""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    interval: Mapped[PlanInterval] = mapped_column(
        Enum(PlanInterval), default=PlanInterval.MONTHLY, nullable=False
    )

    stripe_price_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    stripe_product_id: Mapped[str | None] = mapped_column(String(100))

    email_limit: Mapped[int] = mapped_column(Integer, default=500)
    sms_limit: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription", back_populates="plan"
    )

    def __repr__(self):
        return f"<Plan: {self.name} ${self.price}/{self.interval}>"


class Subscription(UUIDModel):
    """ " A user's active subscription to a plan"""

    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))

    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    sms_sent: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User", back_populates="subscription")
    plan: Mapped[Plan] = relationship("Plan", back_populates="subscriptions")

    @property
    def is_active(self) -> bool:
        return self.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}

    def __repr__(self) -> str:
        return (
            f"<Subscription: {self.user_id} plan={self.plan_id} status={self.status}>"
        )
