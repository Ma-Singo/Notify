from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response

from app.core.authentication import (
    decode_token,
    create_access_token,
    create_refresh_token,
)
from app.schemas.users import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.services.user_service import UserService
from app.api.deps import DBSession
from app.core.rate_limit import limit_auth
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limit_auth
async def login_for_access_token(
    request: Request,
    response: Response,
    db: DBSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    token = await UserService(db).authenticate(form_data.username, form_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    return token


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limit_auth
async def register(
    request: Request, response: Response, payload: UserCreate, db: DBSession
) -> UserRead:
    """Create a new user and fire the account-created notification hook"""
    try:
        user = await UserService(db).create(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
@limit_auth
async def login(
    request: Request, response: Response, payload: LoginRequest, db: DBSession
) -> TokenResponse:
    """Authenticate and receive access + refresh tokens."""
    try:
        return await UserService(db).authenticate(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/refresh", response_model=TokenResponse)
@limit_auth
async def refresh_token(
    request: Request, response: Response, payload: RefreshTokenRequest
) -> TokenResponse:
    """Exchange a refresh token for a new access token."""
    try:
        data = decode_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type"
        )

    subject = data["sub"]
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limit_auth
async def forgot_password(
    request: Request, response: Response, email: str, db: DBSession
) -> None:
    """Trigger password-reset notification (email + SMS OTP).

    Rate limit: 10 requests/minute per IP — prevents SMS/email flooding.
    """
    await UserService(db).request_password_reset(email)
