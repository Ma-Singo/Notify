from fastapi import HTTPException, status, Request, Response, APIRouter

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.exceptions import ConflictError, SubscriptionError
from app.core.rate_limit import limit_default
from app.schemas.subscriptions import (
    CheckoutSessionResponse,
    PlanCreate,
    PlanRead,
    SubscriptionRead,
    SubscriptionCancel,
    SubscriptionCreate,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

# ------------ Plans ------------------------


@router.get("/plans", response_model=list[PlanRead])
@limit_default
async def list_plans(
    request: Request, response: Response, db: DBSession
) -> list[PlanRead]:
    """List all active plans."""

    plans = await SubscriptionService(db).list_plans()
    return plans


@router.get(
    "/plans/create", response_model=PlanRead, status_code=status.HTTP_201_CREATED
)
@limit_default
async def create_plan(
    request: Request,
    response: Response,
    payload: PlanCreate,
    _admin: AdminUser,
    db: DBSession,
) -> PlanRead:
    """Admin: Create a new subscription plan."""
    from app.models.subscriptions import Plan

    plan = Plan(**payload.model_dump())
    db.add(plan)
    await db.flush()
    return PlanRead.model_validate(plan)


# ------------ User Subscriptions ------------------------


@router.get("/me", response_model=SubscriptionRead | None)
@limit_default
async def get_my_subscription(
    request: Request, response: Response, current_user: CurrentUser, db: DBSession
) -> SubscriptionRead | None:
    """Get the current user's subscription."""
    sub = await SubscriptionService(db).get_user_subscription(current_user.id)
    return SubscriptionRead.model_validate(sub) if sub else None


@router.post("/checkout", response_model=CheckoutSessionResponse)
@limit_default
async def create_checkout(
    request: Request,
    response: Response,
    payload: SubscriptionCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> CheckoutSessionResponse:
    """Generate a Stripe Checkout URL for the chosen plan."""
    try:
        return await SubscriptionService(db).create_checkout_session(
            current_user, payload
        )
    except (ConflictError, SubscriptionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/cancel", response_model=SubscriptionRead)
@limit_default
async def cancel_subscription(
    request: Request,
    response: Response,
    payload: SubscriptionCancel,
    current_user: CurrentUser,
    db: DBSession,
) -> SubscriptionRead:
    """Cancel the current user's subscription; fires canceled notification hook."""
    try:
        sub = await SubscriptionService(db).cancel_subscription(current_user, payload)
    except SubscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SubscriptionRead.model_validate(sub)
