from pathlib import Path

import pytest
from pydantic import ValidationError

from auth_api.settings import Settings


ROOT = Path(__file__).resolve().parents[3]


def test_auth_api_dockerfile_execs_uvicorn_from_shell():
    dockerfile = (ROOT / "services/auth-api/Dockerfile").read_text()

    assert "COPY packages/auth-core ./packages/auth-core" in dockerfile
    assert "RUN pip install --no-cache-dir ./packages/auth-core ./services/auth-api" in dockerfile
    assert 'CMD ["sh", "-c", "exec uvicorn auth_api.app:app --host ${AUTH_API_HOST} --port ${AUTH_API_PORT}"]' in dockerfile


def test_settings_default_to_native_auth_database_path(monkeypatch):
    monkeypatch.delenv("AUTH_API_DB_PATH", raising=False)
    monkeypatch.delenv("AUTH_DB_PATH", raising=False)

    settings = Settings()

    assert settings.auth_db_path == "./auth-api.sqlite3"


def test_otlp_upstream_accepts_base_url_and_normalizes_trailing_slash():
    settings = Settings(otlp_upstream="https://otel.example.com/base/")

    assert settings.otlp_upstream == "https://otel.example.com/base"


def test_otlp_upstream_treats_empty_string_as_unset():
    settings = Settings(otlp_upstream="")

    assert settings.otlp_upstream is None


def test_otlp_upstream_authorization_trims_configured_header_value():
    settings = Settings(otlp_upstream_authorization="  Bearer upstream-secret  ")

    assert settings.otlp_upstream_authorization == "Bearer upstream-secret"


def test_otlp_upstream_authorization_treats_empty_string_as_unset():
    settings = Settings(otlp_upstream_authorization="")

    assert settings.otlp_upstream_authorization is None


def test_otlp_upstream_authorization_rejects_multiple_header_lines():
    with pytest.raises(ValidationError):
        Settings(otlp_upstream_authorization="Bearer one\nAuthorization: Bearer two")


@pytest.mark.parametrize(
    "value",
    [
        "collector.example.internal:4318",
        "https://otel.example.com/v1/logs",
        "https://otel.example.com/base?token=abc",
        "https://otel.example.com/base#fragment",
    ],
)
def test_otlp_upstream_rejects_non_base_urls(value):
    with pytest.raises(ValidationError):
        Settings(otlp_upstream=value)
