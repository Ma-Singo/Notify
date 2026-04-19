import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.schemas.users import UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile including subscription."""
    return UserRead.model_validate(current_user)


@router.patch("/me/update", response_model=UserRead)
async def update_me(
    payload: UserUpdate, current_user: CurrentUser, db: DBSession
) -> UserRead:
    user = await UserService(db).update(current_user.id, payload)
    return UserRead.model_validate(user)


@router.delete("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(current_user: CurrentUser, db: DBSession) -> None:
    """Delete own account; fires account-deleted notification hook."""
    await UserService(db).delete(current_user.id)


# -------------- Admin Routes -------------------


@router.delete("/admin/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, _admin: AdminUser, db: DBSession) -> None:
    try:
        await UserService(db).delete(user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
