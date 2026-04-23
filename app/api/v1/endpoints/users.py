import uuid

from fastapi import APIRouter, HTTPException, status, Request, Response

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.core.rate_limit import limit_default
from app.schemas.users import UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
@limit_default
async def get_me(
    request: Request, response: Response, current_user: CurrentUser
) -> UserRead:
    """Return the authenticated user's profile including subscription."""
    return UserRead.model_validate(current_user)


@router.patch("/me/update", response_model=UserRead)
@limit_default
async def update_me(
    request: Request,
    response: Response,
    payload: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserRead:
    user = await UserService(db).update(current_user.id, payload)
    return UserRead.model_validate(user)


@router.delete("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
@limit_default
async def delete_me(
    request: Request, response: Response, current_user: CurrentUser, db: DBSession
) -> None:
    """Delete own account; fires account-deleted notification hook."""
    await UserService(db).delete(current_user.id)


# -------------- Admin Routes -------------------
@router.get("/{user_id}", response_model=UserRead)
@limit_default
async def get_user(
    request: Request,
    response: Response,
    user_id: uuid.UUID,
    _admin: AdminUser,
    db: DBSession,
) -> UserRead:
    """Admin: fetch any user by ID.

    Rate limit: 60 requests/minute per admin user-id.
    """
    try:
        user = await UserService(db).get_user_by_id(user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return UserRead.model_validate(user)


@router.delete("/admin/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limit_default
async def delete_user(
    request: Request,
    response: Response,
    user_id: uuid.UUID,
    _admin: AdminUser,
    db: DBSession,
) -> None:
    try:
        await UserService(db).delete(user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
