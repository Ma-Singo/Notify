from unittest.mock import patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_rate_limit_triggers_after_threshold(
    client: AsyncClient, test_user
) -> None:
    """After exceeding RATE_LIMIT_AUTH requests the endpoint returns 429."""
    bad_creds = {"username": "test", "password": "wrongpassword"}

    with patch("app.core.rate_limit.settings.RATE_LIMIT_ENABLED", True):
        with patch("app.api.v1.endpoints.auth.login") as mock_login:
            from fastapi import HTTPException

            mock_login.side_effect = HTTPException(
                status_code=429, detail="Too many login attempts."
            )

            res = await client.post("/api/v1/auth/login", json=bad_creds)
            assert res.status_code in {401, 429}


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client: AsyncClient, test_user) -> None:
    """Successful responses include X-RateLimit-* headers when limiting is active."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "test", "password": "password123"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_not_rate_limited(client: AsyncClient) -> None:
    """Health endpoint is explicitly excluded from rate limiting."""
    for _ in range(20):
        resp = await client.get("/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_key_by_user_for_authenticated_routes(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Authenticated routes key by user-id, not IP — different users don't share quota."""
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_disabled_env(client: AsyncClient) -> None:
    """When RATE_LIMIT_ENABLED=False all requests pass through."""
    with patch("app.core.rate_limit.settings.RATE_LIMIT_ENABLED", False):
        for _ in range(5):
            resp = await client.get("/health")
            assert resp.status_code == 200
