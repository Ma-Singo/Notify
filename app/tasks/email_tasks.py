import structlog
import asyncio
from celery import Task
from fastapi_mail import FastMail, MessageSchema, MessageType


from app.core.config import settings
from app.core.mail_config import mail_config, render_template
from app.tasks.log_tasks import update_notification_log
from app.worker import celery_app

logger = structlog.get_logger(__name__)


async def _send_email(to: str, subject: str, html: str) -> None:
    message = MessageSchema(
        subject=subject,
        recipients=[to],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(mail_config)
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
        html = render_template(
            "account_created.html",
            {"name": user_name or user_email, "app_name": settings.APP_NAME},
        )
        asyncio.get_event_loop().run_until_complete(
            _send_email(user_email, f"Welcome to {settings.APP_NAME}!", html)
        )
        _update_log(log_id, "sent")
        logger.info("account_created email sent", recipient=user_email)
        return "sent"
    except Exception as exc:
        logger.error("email send failed", error=str(exc), recipient=user_email)
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


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
    try:
        html = render_template(
            "account_deleted.html",
            {"name": user_name or user_email, "app_name": settings.APP_NAME},
        )
        asyncio.get_event_loop().run_until_complete(
            _send_email(
                user_email, f"Your {settings.APP_NAME} account has been deleted", html
            )
        )
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


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
    try:
        html = render_template(
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
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


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
        html = render_template(
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
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_custom_email",
    max_retries=3,
    default_retry_delay=30,
    queue="emails",
)
def send_custom_email(self: Task, to: str, subject: str, body: str, log_id: str) -> str:
    try:
        asyncio.get_event_loop().run_until_complete(_send_email(to, subject, body))
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


# ── Log helper (sync) ─────────────────────────────────────────────────────────


def _update_log(log_id: str, status: str, error: str | None = None) -> None:
    """Fire-and-forget log update via a separate small task."""
    update_notification_log.delay(log_id, status, error)
