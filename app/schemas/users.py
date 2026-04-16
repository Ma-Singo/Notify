import uuid
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr

from app.models.users import UserRole


class UserBase(BaseModel):
    username: str | None = None
    email: EmailStr
    phone: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=64)


class UserUpdate(BaseModel):
    username: str | None = None
    phone: str | None = None
    password: str | None = Field(min_length=8, max_length=64, default=None)


class UserRead(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


# ----------- AUTH -----------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
