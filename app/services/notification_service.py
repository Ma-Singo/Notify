from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
    Notification,
)
from app.models.users import User


class NotificationService:
    """
    Centralized notification service
    Call `fire_event` after user action,
    and it will create a DB log entry then enqueue the appropriate celery task
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def fire_event(
        self, user: User, event: NotificationEvent, extra: dict[str, Any] | None = None
    ) -> list[Notification]:
        """Dispatch email + sms (if phone present) for the given lifecycle event."""

        extra = extra or {}
        logs: list[Notification] = []

        email_log = await self._create_log(
            user=user,
            channel=NotificationChannel.EMAIL,
            event=event,
            recipient=user.email,
        )

        logs.append(email_log)
        self._dispatch_email(event=event, user=user, log=email_log, extra=extra)

        if user.phone:
            sms_log = await self._dispatch_sms(
                user=user,
                channel=NotificationChannel.SMS,
                event=event,
                recipient=user.phone,
            )
            logs.append(sms_log)
            self._dispatch_sms(event=event, user=user, log=sms_log, extra=extra)

        await self.db.flush()
        return logs

    # ---- helper ------------

    async def _create_log(
        self,
        user: User,
        event: NotificationEvent,
        channel: NotificationChannel,
        recipient: str,
        subject: str | None = None,
    ) -> Notification:
        log = Notification(
            user_id=user.id,
            channel=channel,
            event=event,
            status=NotificationStatus.QUEUED,
            recipient=recipient,
            subject=subject,
        )
        self.db.add(log)
        return log


# ---------- Email Dispatch -----------
def _dispatch_email(
        self,
        event: NotificationEvent,
        user: User,
        log: Notification,
        extra: dict[str, Any],
) -> None:
    from app.tasks.email_tasks import (
        send_account_created_email,
        send_account_deleted_email,
        send_password_reset_email,
        send_subscription_email,
    )

    log_id = str(log.id)
    name = user.username or user.email

    if event == NotificationEvent.ACCOUNT_CREATED:
        send_account_created_email.delay(user.email, name, log_id)

    elif event == NotificationEvent.ACCOUNT_DELETED:
        send_account_deleted_email.delay(user.email, name, log_id)

    elif event == NotificationEvent.PASSWORD_RESET:
        reset_url = extra.get("reset_url", str(extra.get("reset_url", "#")))
        send_password_reset_email.delay(user.email, name, reset_url, log_id)

    elif event in {
        NotificationEvent.SUBSCRIPTION_CREATED,
        NotificationEvent.SUBSCRIPTION_CANCELED,
        NotificationEvent.SUBSCRIPTION_RENEWED,
        NotificationEvent.PAYMENT_FAILED,
        NotificationEvent.PAYMENT_SUCCEEDED,
    }:

        send_subscription_email.delay(
            user.email, name, event.value, extra.get("plan_name", ""), log_id
        )


# ----- SMS Dispatch -----------
def _dispatch_sms(
    self,
    event: NotificationEvent,
    user: User,
    log: Notification,
    extra: dict[str, Any],
) -> None:
    from app.tasks.sms_tasks import (
        send_account_created_sms,
        send_account_deleted_sms,
        send_password_reset_sms,
        send_subscription_sms,
    )

    phone = user.phone
    log_id = str(log.id)
    name = user.username or user.email

    if event == NotificationEvent.ACCOUNT_CREATED:
        send_account_created_sms.delay(phone, log_id, name)
    elif event == NotificationEvent.ACCOUNT_DELETED:
        send_account_deleted_sms.delay(phone, log_id)
    elif event == NotificationEvent.PASSWORD_RESET:
        otp = extra.get("otp", "")
        send_password_reset_sms.delay(phone, log_id, otp)
    elif event in {
            NotificationEvent.SUBSCRIPTION_CREATED,
            NotificationEvent.SUBSCRIPTION_CANCELED,
            NotificationEvent.SUBSCRIPTION_RENEWED,
            NotificationEvent.PAYMENT_FAILED,
            NotificationEvent.PAYMENT_SUCCEEDED,
        }:
            send_subscription_sms.delay(phone, event.value, extra.get("plan_name", ""), log_id)


    async def _create_log(
        self,
        user: User,
        channel: NotificationChannel,
        event: NotificationEvent,
        recipient: str,
        subject: str | None = None,
    ) -> Notification:
        log = Notification(
            user_id=user.id,
            channel=channel,
            event=event,
            status=NotificationStatus.QUEUED,
            recipient=recipient,
            subject=subject,
        )
        self.db.add(log)
        return log

