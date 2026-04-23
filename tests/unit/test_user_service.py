import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import verify_password
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_create_user_success(db_session: AsyncSession) -> None:
    payload = UserCreate(
        email="newuser@example.com", password="secret123", username="newuser"
    )
    service = UserService(db_session)
    user = await service.create(payload)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.username == "newuser"
    assert verify_password("secret123", user.hashed_password)


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session: AsyncSession, test_user) -> None:
    payload = UserCreate(
        email=test_user.email, password="wrongpassword", username=test_user.username
    )
    with pytest.raises(ValueError):
        await UserService(db_session).create(payload)


@pytest.mark.asyncio
async def test_authenticate_success(db_session: AsyncSession, test_user: User) -> None:
    service = UserService(db_session)
    tokens = await service.authenticate(test_user.username, "password123")
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession, test_user: User) -> None:
    service = UserService(db_session)
    updated = await service.update(test_user.id, UserUpdate(username="updated"))
    assert updated.username == "updated"


@pytest.mark.asyncio
async def test_delete_user(db_session: AsyncSession, test_user: User) -> None:
    service = UserService(db_session)
    await service.delete(test_user.id)
    await db_session.commit()
    with pytest.raises(ValueError):
        await service.get_user_by_id(test_user.id)
