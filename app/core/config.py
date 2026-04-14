from functools import lru_cache
from typing import Literal
from pathlib import Path


from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

print(BASE_DIR)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        extra="ignore"
    )

    ##########################################
    # Application
    ##########################################
    APP_NAME: str = "NotifyFlow"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    ALLOWED_HOSTS: list[str] = ["*"]
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: AnyHttpUrl = "http://localhost:8000"

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
