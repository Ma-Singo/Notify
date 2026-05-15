from kombu import Queue, Exchange
from celery.schedules import crontab

from app.core.config import settings


class CeleryConfig:
    # -------------------------
    # Core
    # -------------------------
    broker_url: str = settings.CELERY_BROKER_URL
    result_backend: str = settings.CELERY_RESULT_BACKEND

    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list[str] = ["json"]
    timezone: str = "UTC"
    enable_utc: bool = True

    # -------------------------
    # RedBeat Scheduler
    # -------------------------
    redbeat_redis_url: str = settings.CELERY_BROKER_URL
    beat_scheduler: str = "redbeat.RedbeatScheduler"

    redbeat_lock_timeout: int = 3600
    redbeat_lock_retry: bool = True
    redbeat_lock_retry_interval: int = 30
    redbeat_lock_retry_limit: int = 10

    # -------------------------
    # Task Routing (Queues)
    # -------------------------
    task_default_queue: str = "default"
    task_default_exchange: str = "default"
    task_default_routing_key: str = "default"

    task_queues = (
        Queue("default", Exchange("default"), routing_key="default"),
        Queue(
            "emails",
            Exchange("emails"),
            routing_key="emails",
        ),
        Queue("sms", Exchange("sms"), routing_key="sms"),
        Queue("billing", Exchange("billing"), routing_key="billing"),
    )

    task_routes = {
        "app.tasks.email_tasks.*": {"queue": "emails"},
        "app.tasks.sms_tasks.*": {"queue": "sms"},
        # "app.tasks.webhooks.*": {"queue": "webhooks"},
        "app.tasks.billing.*": {"queue": "billing"},
        "app.tasks.log_tasks.*": {"queue": "default"},
    }

    # -------------------------
    # Rate Limiting
    # -------------------------
    task_annotations = {
        "app.tasks.email_tasks.*": {"rate_limit": "100/m"},
        "app.tasks.sms_tasks.*": {"rate_limit": "20/m"},
        "app.tasks.webhooks.*": {"rate_limit": "300/m"},
        "app.tasks.billing.*": {"rate_limit": "100/m"},
    }

    # -------------------------
    # Beat Scheduler (Periodic Tasks)
    # -------------------------
    beat_schedule = {
        "reset-monthly-usage-counters": {
            "task": "app.tasks.billing_tasks.reset_usage_counters",
            "schedule": crontab(day_of_month="1", hour="0", minute="0"),
        },
        "expire-past-due-subscriptions": {
            "task": "app.tasks.billing_tasks.expire_past_due_subscriptions",
            "schedule": crontab(hour="*/6"),
        },
    }

    # -------------------------
    # Retry Behavior
    # -------------------------
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1
    task_time_limit: int = 300
    task_soft_time_limit: int = 240

    task_default_retry_delay: int = 60
    task_max_retries: int = 3
