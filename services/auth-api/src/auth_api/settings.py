from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    auth_db_path: str = Field(
        default="/data/auth-api.sqlite3",
        validation_alias=AliasChoices("AUTH_API_DB_PATH", "AUTH_DB_PATH", "auth_db_path"),
    )
    otlp_upstream: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AOTEL_OTLP_UPSTREAM", "OTLP_UPSTREAM", "otlp_upstream"),
    )
    gateway_max_body_bytes: int = Field(
        default=32 * 1024 * 1024,
        validation_alias=AliasChoices("AOTEL_GATEWAY_MAX_BODY_BYTES", "gateway_max_body_bytes"),
    )
    gateway_forward_timeout_seconds: float = Field(
        default=10.0,
        validation_alias=AliasChoices(
            "AOTEL_GATEWAY_FORWARD_TIMEOUT_SECONDS",
            "gateway_forward_timeout_seconds",
        ),
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)
