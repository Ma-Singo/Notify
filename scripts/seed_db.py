"""
Seed the database with default plans.
Usage:
    $ python manage.py seed
"""

from app.db.session import AsyncSessionLocal
from app.models.subscriptions import Plan, PlanInterval

from sqlalchemy.dialects.postgresql import insert as pg_insert


PLANS = [
    {
        "name": "Starter",
        "slug": "starter",
        "description": "Perfect for individuals and small project",
        "price": 9.00,
        "interval": PlanInterval.MONTHLY,
        "email_limit": 500,
        "sms_limit": 50,
    },
    {
        "name": "Pro",
        "slug": "pro",
        "description": "For growing teams that need more power",
        "price": 29.00,
        "interval": PlanInterval.MONTHLY,
        "email_limit": 5_000,
        "sms_limit": 500,
    },
    {
        "name": "Business",
        "slug": "business",
        "description": "High-volume notifications at scale",
        "price": 79.00,
        "interval": PlanInterval.MONTHLY,
        "email_limit": 50_000,
        "sms_limit": 5_000,
    },
    {
        "name": "Pro Annual",
        "slug": "pro-annual",
        "description": "Pro Plan - billed yearly (2 months free)",
        "price": 290.00,
        "interval": PlanInterval.YEARLY,
        "email_limit": 5_000,
        "sms_limit": 500,
    },
]


async def seed_db() -> None:
    async with AsyncSessionLocal() as session:
        for plan_data in PLANS:
            stmt = (
                pg_insert(Plan)
                .values(**plan_data)
                .on_conflict_do_nothing(index_elements=["slug"])
            )
            result = await session.execute(stmt)
            if result.rowcount:
                print(f"  [+] Created plan '{plan_data['slug']}'")
            else:
                print(f"  [skip] Plan '{plan_data['slug']}' already exists.")

        await session.commit()
        print("\nSeeding complete.")
