import stripe
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.services.subscription_service import SubscriptionService


async def sync_stripe_plans():
    """Sync all seeded plans with Stripe Products and Prices"""
    async with AsyncSessionLocal() as db:
        stripe.api_key = settings.STRIPE_API_KEY

        plans = await SubscriptionService(db).list_plans()

        for plan in plans:
            # Create or retrieve Product
            try:
                products = stripe.Product.list(
                    metadata={"plan_id": str(plan.id)}, limit=1
                )
                if products.data:
                    product = products.data[0]
                else:
                    product = stripe.Product.create(
                        name=plan.name,
                        description=plan.description,
                        metadata={"plan_id": str(plan.id)},
                    )
                    print(f"  [+] Created Product {product.name} ({product.id})")
            except stripe.error.StripeError as e:
                print(f"Stripe error creating product for {plan.name}: {e}")
                continue

            # Create or retrieve Price
            try:
                prices = stripe.Price.list(metadata={"plan_id": str(plan.id)}, limit=1)
                if prices.data:
                    price = prices.data[0]

                    plan.stripe_price_id = price.id
                    print(f"Found existing price: {price.id} for {plan.name}")
                else:
                    if plan.interval == "yearly":
                        price = stripe.Price.create(
                            product=product.id,
                            unit_price=int(plan.price * 100),
                            currency="usd",
                        )
                        print(f"  [+] Created Product {product.name} ({product.id})")
                    else:
                        price = stripe.Price.create(
                            product=product.id,
                            unit_price=int(plan.price),
                            currency="usd",
                            recurring={"interval": "month", "frequency": 1},
                        )

                    plan.stripe_price_id = price.id
                    print(
                        f"  [+] Created Price {price.id} (${plan.price}/{plan.interval})"
                    )
            except stripe.error.StripeError as e:
                print(f"Stripe error creating price for {plan.name}: {e}")
                continue
