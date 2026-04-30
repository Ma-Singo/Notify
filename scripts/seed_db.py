"""
Seed the database with default plans.
Usage:
    $ python manage.py seed
"""

from app.db.session import AsyncSessionLocal, Base, engine
from app.models.subscriptions import Plan, PlanInterval

from sqlalchemy import select


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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for plan_data in PLANS:
            existing = await session.execute(
                select(Plan).where(Plan.slug == plan_data["slug"])
            )
            if existing.scalar_one_or_none():
                print(f"  [skip] Plan '{plan_data['slug']}' already exists.")
                continue
            plan = Plan(**plan_data)
            session.add(plan)
            print(f"  [+] Created plan '{plan_data['slug']}'")

        await session.commit()
        print("\nSeeding complete.")
