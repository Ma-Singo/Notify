from functools import lru_cache
from typing import Literal
from pathlib import Path


from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

print(BASE_DIR)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", case_sensitive=False, extra="ignore"
    )

    ##########################################
    # Application
    ##########################################
    APP_NAME: str = "Notify"
    APP_VERSION: str
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_HOSTS: list[str] = ["*"]
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: AnyHttpUrl = "http://localhost:8000"

    ##########################################
    # REDIS / CELERY
    ##########################################
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    ##########################################
    # DATABASE
    ##########################################
    SQLALCHEMY_DATABASE_URL: str = "sqlite+aiosqlite:///./db.sqlite3"
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    ##########################################
    # ACCESS TOKEN
    ##########################################
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    JWT_ALGORITHM: str

    ##########################################
    # TWILIO (SMS)
    ##########################################
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_FROM_NUMBER: str

    ##########################################
    # EMAIL CONFIGURATION
    ##########################################
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str = "Notify"
    MAIL_PORT: int = 587
    MAIL_SERVER: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    ##########################################
    # Rate Limiting
    ##########################################

    # Format: "N/period"  e.g. "5/minute", "100/hour", "1000/day"
    RATE_LIMIT_ENABLED: bool = True
    # Sensitive auth endpoints (login, register, forgot-password)
    RATE_LIMIT_AUTH: str = "10/minute"
    # General authenticated API calls
    RATE_LIMIT_DEFAULT: str = "60/minute"
    # Notification send endpoints (email / SMS manual triggers)
    RATE_LIMIT_NOTIFICATIONS: str = "30/minute"
    # Stripe webhook — generous; Stripe may burst
    RATE_LIMIT_WEBHOOKS: str = "300/minute"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_staging(self) -> bool:
        return self.APP_ENV == "staging"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
