import uuid
from datetime import datetime, timezone

import stripe
import structlog

from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import select

from app.api.deps import DBSession
from app.core.config import settings
from app.core.rate_limit import limit_webhooks
from app.models.users import User
from app.models.notifications import NotificationEvent
from app.services.notification_service import NotificationService
from app.services.subscription_service import SubscriptionService
from app.models.subscriptions import Subscription, SubscriptionStatus


router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = structlog.get_logger(__name__)

stripe.api_key = settings.STRIPE_API_KEY


@router.get("/stripe", status_code=status.HTTP_200_OK)
@limit_webhooks
async def stripe_webhook(request: Request, db: DBSession) -> dict[str, str]:
    """Stripe signed webhook receiver"""
    payload = await request.body()
    signed_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signed_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except "ValueError, stripe.error.SignatureVerificationError":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        )
    service = SubscriptionService(db)
    event_type: str = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("mode") == "subscription":
            meta = session.get("meta", {})
            stripe_sub = stripe.Subscription.retrieve(session["subscription"])
            period = (
                stripe_sub["current_period_start"],
                stripe_sub["current_period_end"],
            )
            await service.activate_subscription(
                user_id=uuid.UUID(meta["user_id"]),
                stripe_subscription_id=stripe_sub["id"],
                stripe_customer_id=session["customer"],
                plan_id=uuid.UUID(meta["plan_id"]),
                period_start=datetime.fromtimestamp(period[0], tz=timezone.utc),
                period_end=datetime.fromtimestamp(period[1], tz=timezone.utc),
            )
    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        stripe_sub_id = invoice.get("subscription")
        if stripe_sub_id:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_sub_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub and sub.status == SubscriptionStatus.PAST_DUE:
                sub.status = SubscriptionStatus.ACTIVE
                user_result = await db.execute(
                    select(User).where(User.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    plan_name = sub.plan.name if sub.plan else ""
                    await NotificationService(db).fire_event(
                        user,
                        NotificationEvent.PAYMENT_FAILED,
                        extra={"plan_name": plan_name},
                    )

    elif event_type == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        stripe_sub_id = invoice.get("subscription")
        if stripe_sub_id:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_sub_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub and sub.status == SubscriptionStatus.PAST_DUE:
                sub.status = SubscriptionStatus.ACTIVE
                user_result = await db.execute(
                    select(User).where(User.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    plan_name = sub.plan.name if sub.plan else ""
                    await NotificationService(db).fire_event(
                        user,
                        NotificationEvent.PAYMENT_SUCCEEDED,
                        extra={"plan_name": plan_name},
                    )
    logger.info("stripe webhook triggered", type=event_type)
    return {"status": "ok"}
