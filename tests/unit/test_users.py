from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict) -> None:
    res = await client.get("/api/v1/users/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "test"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient) -> None:
    res = await client.get("/api/v1/users/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient, auth_headers: dict) -> None:
    res = await client.patch(
        "/api/v1/users/me/update", headers=auth_headers, json={"username": "test2"}
    )
    assert res.status_code == 200
    assert res.json()["username"] == "test2"


@pytest.mark.asyncio
async def test_delete_me(client: AsyncClient, auth_headers: dict) -> None:
    with patch(
        "app.services.notification_service.NotificationService.fire_event",
        new_callable=AsyncMock,
    ):
        res = await client.delete("/api/v1/users/me/delete", headers=auth_headers)
    assert res.status_code == 204
