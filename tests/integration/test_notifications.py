import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import (
    Notification,
    NotificationEvent,
    NotificationChannel,
    NotificationStatus,
)
from app.models.users import User


@pytest.mark.asyncio
async def test_list_notifications_empty(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
) -> None:
    res = await client.get("/api/v1/notifications/", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_notifications_data(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
) -> None:
    log = Notification(
        user_id=test_user.id,
        channel=NotificationChannel.EMAIL,
        event=NotificationEvent.ACCOUNT_CREATED,
        status=NotificationStatus.SENT,
        recipient=test_user.email,
    )

    db_session.add(log)
    await db_session.commit()

    res = await client.get("/api/v1/notifications/", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["channel"] == "email"
    assert body["items"][0]["event"] == "account_created"
