
import structlog
from celery import Task
from twilio.rest import Client

from app.core.config import settings
from app.worker import celery_app

logger = structlog.get_logger(__name__)


def _get_twilio_client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


# ── Tasks ─────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.tasks.sms_tasks.send_account_created_sms",
    max_retries=3,
    default_retry_delay=30,
    queue="sms",
)
def send_account_created_sms(self: Task, phone: str, user_name: str, log_id: str) -> str:
    try:
        client = _get_twilio_client()
        body = f"Welcome to {settings.APP_NAME}, {user_name}! Your account is ready."
        client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER, body=body)
        _update_log(log_id, "sent")
        logger.info("account_created sms sent", recipient=phone)
        return "sent"
    except Exception as exc:
        logger.error("sms send failed", error=str(exc), recipient=phone)
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.sms_tasks.send_account_deleted_sms",
    max_retries=3,
    default_retry_delay=30,
    queue="sms",
)
def send_account_deleted_sms(self: Task, phone: str, log_id: str) -> str:
    try:
        client = _get_twilio_client()
        body = f"Your {settings.APP_NAME} account has been successfully deleted. Thank you."
        client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER, body=body)
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.sms_tasks.send_password_reset_sms",
    max_retries=3,
    default_retry_delay=30,
    queue="sms",
)
def send_password_reset_sms(self: Task, phone: str, otp: str, log_id: str) -> str:
    try:
        client = _get_twilio_client()
        body = f"Your {settings.APP_NAME} password reset code is: {otp}. Expires in 15 minutes."
        client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER, body=body)
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.sms_tasks.send_subscription_sms",
    max_retries=3,
    default_retry_delay=30,
    queue="sms",
)
def send_subscription_sms(
    self: Task, phone: str, event: str, plan_name: str, log_id: str
) -> str:
    messages = {
        "subscription_created": f"You're now on the {plan_name} plan. Enjoy {settings.APP_NAME}!",
        "subscription_canceled": f"Your {settings.APP_NAME} subscription has been canceled.",
        "subscription_renewed": f"Your {plan_name} subscription has been renewed. Thanks!",
        "payment_failed": f"Action required: Your {settings.APP_NAME} payment failed. Please update your payment method.",
        "payment_succeeded": f"Payment confirmed for your {plan_name} plan. Thank you!",
    }
    body = messages.get(event, f"Update on your {settings.APP_NAME} subscription.")
    try:
        client = _get_twilio_client()
        client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER, body=body)
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.sms_tasks.send_custom_sms",
    max_retries=3,
    default_retry_delay=30,
    queue="sms",
)
def send_custom_sms(self: Task, to: str, body: str, log_id: str) -> str:
    try:
        client = _get_twilio_client()
        client.messages.create(to=to, from_=settings.TWILIO_FROM_NUMBER, body=body)
        _update_log(log_id, "sent")
        return "sent"
    except Exception as exc:
        _update_log(log_id, "retrying", str(exc))
        raise self.retry(exc=exc)


def _update_log(log_id: str, status: str, error: str | None = None) -> None:
    from app.tasks.email_tasks import update_notification_log
    update_notification_log.delay(log_id, status, error)
