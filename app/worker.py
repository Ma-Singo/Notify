from celery import Celery
from celery.schedules import crontab
from kombu import Queue


from app.core.config import settings

celery_app = Celery(settings.APP_NAME)

celery_app.config_from_object(
    {
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_queues": (
            Queue("defaults"),
            Queue("emails"),
            Queue("sms"),
            Queue("webhooks"),
        ),
        "task_default_queue": "default",
        "task_routes": {
            "app.tasks.email_tasks.*": {"queue": "emails"},
            "app.tasks.sms_tasks.*": {"queue": "sms"},
            "app.tasks.webhooks.*": {"queue": "webhooks"},
            # Rate limiting for critical queues
        },
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "task_max_retries": 3,
        "task_default_retry_delay": 60,
        "result_expires": 3600,
        "beat_schedule": {
            "reset-monthly-usage-counters": {
                "task": "app.tasks.billing_tasks.reset_monthly_usage_counters",
                "schedule": crontab(day_of_month="1", hour="0", minute="0"),
            },
            "expire-past-due-subscriptions": {
                "task": "app.tasks.billing_tasks.expire_past_due_subscriptions",
                "schedule": crontab(hour="*/6"),
            },
            # TODO
            "cleanup-failed-tasks": {
                "task": "app.tasks.cleanup_tasks.cleanup_failed_tasks",
                "schedule": crontab(hour="2", minute="0"),  # Daily at 2 AM
            },
            "health-check": {
                "task": "app.tasks.monitoring_tasks.health_check",
                "schedule": crontab(minute="*/5"),  # Every 5 minutes
            },
        },
        "timezone": "UTC",
        "enable_utc": True,
    }
)
celery_app.autodiscover_tasks("app.tasks")
