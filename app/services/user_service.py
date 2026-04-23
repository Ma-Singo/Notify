import uuid
import structlog

from app.schemas.notifications import NotificationEvent
from app.services.notification_service import NotificationService
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


logger = structlog.getLogger(__name__)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifier = NotificationService(db)

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
        result = await self.db.execute(select(User).where(User.username == username))
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
        await self.db.flush()

        await self.notifier.fire_event(
            user,
            NotificationEvent.ACCOUNT_UPDATED,
        )
        logger.info("user created", user_id=str(user.id), email=user.email)
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
        await self.notifier.fire_event(
            user,
            NotificationEvent.ACCOUNT_UPDATED,
        )
        logger.info("user account updated", user_id=str(user.id), email=user.email)
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.get_user_by_id(user_id)
        # Fire ACCOUNT_DELETED hook BEFORE actual delete so user still exists
        await self.notifier.fire_event(
            user,
            NotificationEvent.ACCOUNT_DELETED,
        )
        await self.db.flush()
        await self.db.delete(user)
        logger.info("user deleted", user_id=str(user_id))

    #  ------------ Authentication ---------------
    async def authenticate(self, username: str, password: str) -> TokenResponse:
        user = await self.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def request_password_reset(self, email: str) -> None:
        user = await self.get_user_by_email(email)
        if not user:
            return  # silently ignore unknown emails
        import random

        otp = str(random.randint(100_000, 999_999))
        # 🔔 Fire PASSWORD_RESET hook
        await self.notifier.fire_event(
            event=NotificationEvent.PASSWORD_RESET,
            user=user,
            extra={
                "otp": otp,
                "reset_url": f"http://127.0.0.1:8000/api/v1/auth/reset?token={otp}",
            },
        )
        logger.info("password reset requested", user_id=str(user.id))
