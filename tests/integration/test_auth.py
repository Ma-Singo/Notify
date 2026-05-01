import pytest
from httpx import AsyncClient

from app.models.users import User


@pytest.mark.asyncio
async def test_register(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "register@example.com",
            "password": "securepassword",
            "username": "register",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "register@example.com"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, test_user: User) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "newpassword",
            "username": test_user.username,
        },
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": "password123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_login_wrong_credentials(client: AsyncClient, test_user: User) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": "wrongpassword"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    res = await client.get("/api/v1/users/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient) -> None:
    res = await client.get("/api/v1/users/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
