from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """shared declarative base class for all ORM models"""


if settings.APP_ENV == "development":
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URL,
        future=True,
        echo=settings.DEBUG,
        pool_size=settings.SQLALCHEMY_DATABASE_POOL_SIZE,
        max_overflow=settings.SQLALCHEMY_MAX_OVERFLOW,
    )

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
