import os
from typing import Literal, Self

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
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
    smtp_enabled: bool = False
    smtp_host: str = Field(default="localhost", min_length=1)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: EmailStr = "noreply@example.com"
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = Field(default=10, gt=0)

    @field_validator("smtp_username", "smtp_password", mode="before")
    @classmethod
    def empty_smtp_credentials_to_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_smtp_credentials(self) -> Self:
        username_missing = self.smtp_username is None
        password_missing = self.smtp_password is None
        if username_missing != password_missing:
            raise ValueError(
                "SMTP_USERNAME and SMTP_PASSWORD must be configured together"
            )
        return self


settings = Settings()  # type: ignore[call-arg]
