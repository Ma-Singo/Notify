import uuid
from datetime import datetime, timezone

import stripe
import structlog

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, SubscriptionError
from app.models.notifications import NotificationEvent
from app.models.subscriptions import Plan, Subscription, SubscriptionStatus
from app.models.users import User
from app.services.notification_service import NotificationService
from app.schemas.subscriptions import (
    CheckoutSessionResponse,
    SubscriptionCancel,
    SubscriptionCreate,
)

stripe.api_key = settings.STRIPE_API_KEY

logger = structlog.get_logger(__name__)


class SubscriptionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifier = NotificationService(db)

    # ------------- Plans -------------------
    async def list_plans(self) -> list[Plan]:
        result = await self.db.execute(select(Plan).where(Plan.is_active))
        return list(result.scalars().all())

    async def get_plan(self, plan_id: uuid.UUID) -> Plan:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError(f"Plan with id {plan_id} not found", str(plan_id))
        return plan

    # ------------- Subscriptions -------------------

    async def get_user_subscription(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .options(selectinload(Subscription.plan))
        )
        return result.scalar_one_or_none()

    async def create_checkout_session(
        self, user: User, payload: SubscriptionCreate
    ) -> CheckoutSessionResponse:
        """Create a Stripe checkout session and return  the URL"""
        plan = await self.get_plan(payload.plan_id)

        if not plan.stripe_price_id:
            raise SubscriptionError("Plan is not linked to a stripe price")

        existing = await self.get_user_subscription(user.id)
        if existing and existing.is_active:
            raise ConflictError("User already has an active subscription")

        customer_id = await self._get_or_create_stripe_customer(user)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/subscription/cancel",
            metadata={"user_id": str(user.id), "plan_id": str(plan.id)},
        )
        logger.info("Checkout session created", user_id=str(user.id), plan_id=plan.slug)
        return CheckoutSessionResponse(checkout_url=session.url, session_id=session.id)

    async def activate_subscription(
        self,
        user_id: uuid.UUID,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        plan_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> Subscription:
        """Called by Stripe webhook after successful payment."""
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        plan = await self.get_plan(plan_id)

        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            current_period_start=period_start,
            current_period_end=period_end,
        )
        self.db.add(sub)
        await self.db.flush()

        # Fire SUBSCRIPTION_CREATED hook
        await self.notifier.fire_event(
            user,
            NotificationEvent.SUBSCRIPTION_CREATED,
            extra={"plan_name": plan.name},
        )
        logger.info("subscription activated", user_id=str(user_id), plan=plan.slug)
        return sub

    async def cancel_subscription(
        self, user: User, payload: SubscriptionCancel
    ) -> Subscription:
        sub = await self.get_user_subscription(user.id)
        if sub and sub.stripe_customer_id:
            raise SubscriptionError("No active subscription to cancel")

        if sub.stripe_subscription_id:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=payload.cancel_at_period_end,
            )
        sub.status = SubscriptionStatus.CANCELED
        sub.cancel_at = datetime.now(timezone.utc)
        await self.db.flush()

        plan = sub.plan
        # Fire SUBSCRIPTION_CANCELED hook
        await self.notifier.fire_event(
            user,
            NotificationEvent.SUBSCRIPTION_CANCELED,
            extra={"plan_name": plan.name},
        )
        logger.info("subscription cancelled", user_id=str(user.id))
        return sub

    # ------------- Stripe Helper -------------------

    async def _get_or_create_stripe_customer(self, user: User) -> str:
        sub = await self.get_user_subscription(user.id)
        if sub and sub.stripe_customer_id:
            return sub.stripe_customer_id
        customer = stripe.Customer.create(
            email=user.email,
            name=user.username,
            metadata={"user_id": str(user.id)},
        )
        return customer.id

    # ------------- Usage tracking -------------------

    async def increment_email_usage(self, user_id: uuid.UUID) -> None:
        sub = await self.get_user_subscription(user_id)
        if sub:
            sub.emails_sent += 1

    async def increment_sms_usage(self, user_id: uuid.UUID) -> None:
        sub = await self.get_user_subscription(user_id)
        if sub:
            sub.sms_sent += 1
