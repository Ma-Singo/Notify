import enum
# from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDModel
from app.models.notifications import Notification


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(UUIDModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, unique=True
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.USER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"
