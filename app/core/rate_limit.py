"""
Rate limiting for NotifyFlow.

Strategy
--------
* Uses ``slowapi`` (a Starlette/FastAPI wrapper around ``limits``), backed by Redis
  so limits are shared across all API worker processes.
* Two key dimensions:
    - **Unauthenticated / auth endpoints** → keyed by client IP
    - **Authenticated endpoints** → keyed by user-id (fairer than IP for shared
      networks; also prevents token-farming abuse)
* Each route group (auth, default, notifications, webhooks) has its own limit
  string, all configurable through env vars.
* When rate limiting is disabled (RATE_LIMIT_ENABLED=false) the limiter is a
  no-op — useful for local dev or test environments.
* Standard ``Retry-After``, ``X-RateLimit-*`` headers are injected on every
  response, and a ``429 Too Many Requests`` JSON body is returned on breach.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.core.config import settings


def _get_key_by_ip(request: Request) -> str:
    """Default key: real client IP (handles X-Forwarded-For)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


def _get_key_by_user_or_ip(request: Request) -> str:
    """
    For authenticated routes: use the JWT subject (user-id) extracted from the
    Authorization header — falls back to IP if no token is present so the limiter
    still works on public endpoints using this key function.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from app.core.authentication import decode_token

            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return _get_key_by_ip(request)


def _builder_limiter() -> Limiter:
    if not settings.RATE_LIMIT_ENABLED:
        return Limiter(key_func=_get_key_by_ip, enabled=False)
    return Limiter(
        key_func=_get_key_by_ip,
        #storage=settings.REDIS_URL,
        headers_enabled=True,
        strategy="fixed-window",
    )


limiter: Limiter = _builder_limiter()


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    retry_after = getattr(exc, "retry_after", None)
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": "Too Many Requests",
            "limit": str(exc.limit),
        },
        headers=headers,
    )


def limit_auth(func):  # type: ignore[no-untyped-def]
    """Strict limit for auth endpoints (login, register, forgot-password)."""
    return limiter.limit(settings.RATE_LIMIT_AUTH, key_func=_get_key_by_ip)(func)


def limit_default(func):  # type: ignore[no-untyped-def]
    """General limit for authenticated API routes, keyed by user-id."""
    return limiter.limit(settings.RATE_LIMIT_DEFAULT, key_func=_get_key_by_user_or_ip)(
        func
    )


def limit_notifications(func):  # type: ignore[no-untyped-def]
    """Tighter limit for notification send endpoints."""
    return limiter.limit(
        settings.RATE_LIMIT_NOTIFICATIONS, key_func=_get_key_by_user_or_ip
    )(func)


def limit_webhooks(func):  # type: ignore[no-untyped-def]
    """Generous limit for Stripe webhook receiver."""
    return limiter.limit(settings.RATE_LIMIT_WEBHOOKS, key_func=_get_key_by_ip)(func)
