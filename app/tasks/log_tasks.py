from app.worker import celery_app
from app.core.logging import logger


@celery_app.task(name="app.tasks.log_tasks.update_notification_log", queue="default")
def update_notification_log(log_id: str, status: str, error: str | None = None) -> None:
    import asyncio
    import uuid
    from app.db.session import AsyncSessionLocal
    from app.models.notifications import Notification, NotificationStatus
    from sqlalchemy import select

    # Validate log_id
    if not log_id or log_id == "None" or str(log_id).strip() == "":
        logger.error(
            f"update_notification_log called with invalid log_id: '{log_id}' (type: {type(log_id)})"
        )
        return

    # Try to convert to UUID
    try:
        log_uuid = uuid.UUID(str(log_id))
    except (ValueError, AttributeError, TypeError) as e:
        logger.error(f"Invalid UUID format for log_id: '{log_id}' - Error: {e}")
        return

    async def _update() -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Notification).where(Notification.id == log_uuid)
            )
            log = result.scalar_one_or_none()
            if log:
                log.status = NotificationStatus(status)
                if error:
                    log.error_message = error
                    log.retry_count += 1
                await session.commit()
                logger.info(f"Updated notification {log_id} to status {status}")
            else:
                logger.warning(f"Notification {log_id} not found")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(_update())
    except RuntimeError:
        asyncio.run(_update())
