import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.subscriptions import PlanInterval, SubscriptionStatus


class PlanBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    price: float
    interval: PlanInterval = PlanInterval.MONTHLY
    email_limit: int = 500
    sms_limit: int = 100


class PlanCreate(PlanBase):
    stripe_price_id: str | None = None
    stripe_product_id: str | None = None


class PlanRead(PlanBase):
    id: uuid.UUID
    is_active: bool
    stripe_price_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: SubscriptionStatus
    trial_end: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    canceled_at: datetime | None
    emails_sent: int
    sms_sent: int
    plan: PlanRead

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    plan_id: uuid.UUID
    stripe_payment_method_id: str | None = None


class SubscriptionCancel(BaseModel):
    reason: str | None = None
    cancel_at_period_end: bool = True


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str
