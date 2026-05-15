from celery import Celery

celery_app = Celery("Notify")

celery_app.config_from_object("app.core.celery_config:CeleryConfig")


celery_app.autodiscover_tasks(
    [
        "app.tasks.email_tasks",
        "app.tasks.sms_tasks",
        "app.tasks.billing_tasks",
        "app.tasks.log_tasks",
    ]
)
