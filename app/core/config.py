import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = os.getenv("ENV_FILE", ".env").strip() or ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "development", "test", "staging", "production"] = (
        "local"
    )
    database_url: str = Field(min_length=1)
    redis_url: str = Field(min_length=1)
    jwt_secret_key: str = Field(min_length=1)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


settings = Settings()  # type: ignore[call-arg]
