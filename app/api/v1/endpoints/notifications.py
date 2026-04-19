import math

from fastapi import APIRouter, Query, Request, status

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.models.notifications import (
    Notification,
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)
from app.core.rate_limit import limit_default, limit_notifications
from app.schemas.notifications import (
    NotificationPage,
    NotificationRead,
    SendSMSRequest,
    SendEmailRequest,
)


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationPage)
@limit_default
async def list_my_notifications(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> NotificationPage:
    """Paginated notification history for the current user.

    Rate limit: 60 requests/minute per user-id.
    """
    from sqlalchemy import func, select

    offset = (page - 1) * size
    total_result = await db.execute(
        select(func.count()).where(Notification.user_id == current_user.id)
    )
    total = total_result.scalar_one()
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    items = result.scalars().all()
    return NotificationPage(
        items=[NotificationRead.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 1,
    )


# ── Admin: manual triggers ────────────────────────────────────────────────────


@router.post("/send-email", status_code=status.HTTP_202_ACCEPTED)
@limit_notifications
async def send_custom_email(
    request: Request,
    payload: SendEmailRequest,
    _admin: AdminUser,
    db: DBSession,
) -> dict[str, str]:
    """Admin: manually enqueue a custom email.

    Rate limit: 30 requests/minute per admin user-id — prevents runaway sends.
    """
    from app.tasks.email_tasks import send_custom_email as _task

    log = Notification(
        user_id=payload.user_id,
        channel=NotificationChannel.EMAIL,
        event=NotificationEvent.CUSTOM,
        status=NotificationStatus.QUEUED,
        recipient=payload.to,
        subject=payload.subject,
        body_preview=payload.body[:500],
    )
    db.add(log)
    await db.flush()

    task = _task.delay(payload.to, payload.subject, payload.body, str(log.id))
    log.celery_task_id = task.id
    return {"task_id": task.id, "log_id": str(log.id)}


@router.post("/send-sms", status_code=status.HTTP_202_ACCEPTED)
@limit_notifications
async def send_custom_sms(
    request: Request,
    payload: SendSMSRequest,
    _admin: AdminUser,
    db: DBSession,
) -> dict[str, str]:
    """Admin: manually enqueue a custom SMS.

    Rate limit: 30 requests/minute per admin user-id.
    """
    from app.tasks.sms_tasks import send_custom_sms as _task

    log = Notification(
        user_id=payload.user_id,
        channel=NotificationChannel.SMS,
        event=NotificationEvent.CUSTOM,
        status=NotificationStatus.QUEUED,
        recipient=payload.to,
        body_preview=payload.body[:500],
    )
    db.add(log)
    await db.flush()

    task = _task.delay(payload.to, payload.body, str(log.id))
    log.celery_task_id = task.id
    return {"task_id": task.id, "log_id": str(log.id)}
