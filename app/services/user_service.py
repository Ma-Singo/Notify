import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.core.authentication import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate, TokenResponse


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User", str(user_id))
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == username))
        return result.scalar_one_or_none()

    #  ------------ CRUD Operations ---------------

    async def create(self, payload: UserCreate) -> User:
        exists = await self.get_user_by_email(payload.email)
        if exists:
            raise ConflictError(f"Email '{payload.email}' already exists")
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            username=payload.username,
            phone=payload.phone,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)
        if payload.phone is not None:
            user.phone = payload.phone
        if payload.username is not None:
            user.username = payload.username
        if payload.password is not None:
            user.hashed_password = hash_password(payload.password)
        await self.db.flush()
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.get_user_by_id(user_id)
        await self.db.delete(user)

    #  ------------ Authentication ---------------
    async def authenticate(self, email: str, password: str) -> TokenResponse:
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )
