from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    auth_db_path: str = Field(
        default="./auth-api.sqlite3",
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

    @field_validator("otlp_upstream")
    @classmethod
    def validate_otlp_upstream_base_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        normalized = value.rstrip("/")
        parts = urlsplit(normalized)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("AOTEL_OTLP_UPSTREAM must be an http(s) base URL")
        if parts.query or parts.fragment:
            raise ValueError("AOTEL_OTLP_UPSTREAM must not include query or fragment")
        if parts.path in {"/v1/logs", "/v1/traces", "/v1/metrics"}:
            raise ValueError("AOTEL_OTLP_UPSTREAM must be a base URL; the gateway appends OTLP signal paths")
        return normalized
