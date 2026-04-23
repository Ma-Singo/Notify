from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, test_user) -> None:
    with patch(
        "app.services.notification_service.NotificationService.fire_event",
        new_callable=AsyncMock,
    ):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
                "username": "newuser",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "securepass123",
        "username": "dup",
    }
    with patch(
        "app.services.notification_service.NotificationService.fire_event",
        new_callable=AsyncMock,
    ):
        await client.post("/api/v1/auth/register", json=payload)
        res = await client.post(
            "/api/v1/auth/register",
            json=payload,
        )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
            "username": "test",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword",
            "username": "test",
        },
    )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={"password": "password123", "username": "test"},
    )
    refresh_token = res.json()["refresh_token"]
    res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
