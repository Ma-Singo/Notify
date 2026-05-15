from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi_mail import ConnectionConfig

from app.core.config import settings


# ── Jinja2 template env ───────────────────────────────────────────────────────
_jinja_env = Environment(
    loader=FileSystemLoader("app/templates/email"),
    autoescape=select_autoescape(["html"]),
)

# ── FastAPI-Mail connection config ────────────────────────────────────────────
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER="app/templates/email",
)


def render_template(template_name: str, context: dict[str, Any]) -> str:
    tpl = _jinja_env.get_template(template_name)
    return tpl.render(**context)
