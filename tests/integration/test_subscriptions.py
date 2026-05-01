import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_plans_empty(client: AsyncClient) -> None:
    res = await client.get("/api/v1/subscriptions/plans")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_get_my_subscription_none(
    client: AsyncClient, auth_headers: dict
) -> None:
    res = await client.get("/api/v1/subscriptions/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() is None


@pytest.mark.asyncio
async def test_checkout_requires_valid_plan(
    client: AsyncClient, auth_headers: dict
) -> None:
    res = await client.post(
        "/api/v1/subscriptions/checkout",
        headers=auth_headers,
        json={"plan_id": str(uuid.uuid4())},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
