import uuid
from typing import Any

import structlog
from celery import Task
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.worker import celery_app

logger = structlog.get_logger(__name__)

# ── Jinja2 template env ───────────────────────────────────────────────────────
_jinja_env = Environment(
    loader=FileSystemLoader("app/templates/email"),
    autoescape=select_autoescape(["html"]),
)

# ── FastAPI-Mail connection config ────────────────────────────────────────────
_mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    VALIDATE_CERTS=True,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER="app/templates/email",
)


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


async def _send_email(to: str, subject: str, html: str) -> None:
    message = MessageSchema(
        subject=subject,
        recipients=[to],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(_mail_config)
    await fm.send_message(message)


# ── Tasks ─────────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_account_created_email",
    max_retries=3,
    default_retry_delay=30,
    queue="emails",
)
def send_account_created_email(
    self: Task, user_email: str, user_name: str, log_id: str
) -> str:
    import asyncio

    try:
        html = _render_template(
            "account_created.html",
            {"name": user_name or user_email, "app_name": settings.APP_NAME},
        )
        asyncio.get_event_loop().run_until_complete(
            _send_email(user_email, f"Welcome to {settings.APP_NAME}!", html)
        )
        _update_log(log_id, "sent")
        logger.info("account_created email sent", recipient=user_email)
        return "sent"
    except Exception as e:
        logger.error("email send failed", error=str(e), recipient=user_email)
        _update_log(log_id, "retrying", str(e))
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_account_deleted_email",
    max_retries=3,
    default_retry_delay=30,
    queue="emails",
)
def send_account_deleted_email(
    self: Task, user_email: str, user_name: str, log_id: str
) -> str:
    import asyncio

    try:
        html = _render_template(
            "account_deleted.html",
            {"name": user_name or user_email, "app_name": settings.APP_NAME},
        )
        asyncio.get_event_loop().run_until_complete(
            _send_email(
                user_email, f"Your {settings.APP_NAME} account has been deleted", html
            )
        )
        logger.info("account_deleted email sent", recipient=user_email)
        _update_log(log_id, "sent")
        return "sent"
    except Exception as e:
        logger.error("email delete failed", error=str(e), recipient=user_email)
        _update_log(log_id, "retrying", str(e))
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_password_reset_email",
    max_retries=3,
    default_retry_delay=30,
    queue="emails",
)
def send_password_reset_email(
    self: Task, user_email: str, user_name: str, reset_url: str, log_id: str
) -> str:
    import asyncio

    try:
        html = _render_template(
            "password_reset.html",
            {
                "name": user_name or user_email,
                "reset_url": reset_url,
                "app_name": settings.APP_NAME,
            },
        )
        asyncio.get_event_loop().run_until_complete(
            _send_email(user_email, "Reset your password", html)
        )
        logger.info("password_reset email sent", recipient=user_email)
        _update_log(log_id, "sent")
        return "sent"
    except Exception as e:
        logger.error("email sent failed", error=str(e), recipient=user_email)
        _update_log(log_id, "retrying", str(e))
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_subscription_email",
    max_retries=3,
    default_retry_delay=30,
    queue="emails",
)
def send_subscription_email(
    self: Task,
    user_email: str,
    user_name: str,
    event: str,
    plan_name: str,
    log_id: str,
) -> str:
    import asyncio

    template_map = {
        "subscription_created": (
            "subscription_created.html",
            f"Welcome to {plan_name}!",
        ),
        "subscription_canceled": (
            "subscription_canceled.html",
            "Subscription Canceled",
        ),
        "subscription_renewed": ("subscription_renewed.html", "Subscription Renewed"),
        "payment_failed": ("payment_failed.html", "Action Required: Payment Failed"),
        "payment_succeeded": ("payment_succeeded.html", "Payment Confirmed"),
    }
    template_name, subject = template_map.get(
        event, ("subscription_created.html", "Subscription Update")
    )
    try:
        html = _render_template(
            template_name,
            {
                "name": user_name or user_email,
                "plan_name": plan_name,
                "app_name": settings.APP_NAME,
                "frontend_url": str(settings.FRONTEND_URL),
            },
        )
        asyncio.get_event_loop().run_until_complete(
            _send_email(user_email, subject, html)
        )
        _update_log(log_id, "sent")
        return "sent"
    except Exception as e:
        _update_log(log_id, "retrying", str(e))
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_custom_email",
    max_retries=3,
    default_retry_delay=30,
    queue="emails",
)
def send_custom_email(self: Task, to: str, subject: str, body: str, log_id: str) -> str:
    import asyncio

    try:
        asyncio.get_event_loop().run_until_complete(_send_email(to, subject, body))
        _update_log(log_id, "sent")
        return "sent"
    except Exception as e:
        _update_log(log_id, "retrying", str(e))
        raise self.retry(exc=e)


# ── Log helper (sync) ─────────────────────────────────────────────────────────


def _update_log(log_id: str, status: str, error: str | None = None) -> None:
    """Fire-and-forget log update via a separate small task."""
    update_notification_log.delay(log_id, status, error)


@celery_app.task(name="app.tasks.email_tasks.update_notification_log", queue="default")
def update_notification_log(log_id: str, status: str, error: str | None = None) -> None:
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.models.notifications import Notification, NotificationStatus
    from sqlalchemy import select

    async def _update() -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Notification).where(Notification.id == uuid.UUID(log_id))
            )
            log = result.scalar_one_or_none()
            if log:
                log.status = NotificationStatus(status)
                if error:
                    log.error_message = error
                    log.retry_count += 1
                await session.commit()

    asyncio.get_event_loop().run_until_complete(_update())
