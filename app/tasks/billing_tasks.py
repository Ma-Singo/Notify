import structlog
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.db.session import AsyncSessionLocal
from app.models.subscriptions import Subscription, SubscriptionStatus
from app.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.billing_tasks.reset_usage_counters",
    queue="default",
)
def reset_usage_counters() -> dict[str, int]:
    """Reset email/SMS counters for all active subscriptions at start of billing cycle."""

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(Subscription)
                .where(
                    Subscription.status.in_(
                        [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
                    )
                )
                .values(emails_sent=0, smss_sent=0)
                .returning(Subscription.id)
            )
            rows = result.fetchall()
            await session.commit()
            count = len(rows)
            logger.info("usage counters reset", subscriptions_reset=count)
            return {"subscriptions_reset": count}

    return asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(
    name="app.tasks.billing_tasks.expire_past_due_subscriptions",
    queue="default",
)
def expire_past_due_subscriptions() -> dict[str, int]:
    """Cancel subscriptions that have been past-due for more than 7 days."""

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(Subscription)
                .where(
                    Subscription.status == SubscriptionStatus.PAST_DUE,
                    Subscription.updated_at <= cutoff,
                )
                .values(
                    status=SubscriptionStatus.CANCELED,
                    canceled_at=datetime.now(timezone.utc),
                )
                .returning(Subscription.id)
            )
            rows = result.fetchall()
            await session.commit()
            count = len(rows)
            logger.info("past-due subscriptions expired", count=count)
            return {"expired": count}

    return asyncio.get_event_loop().run_until_complete(_run())
