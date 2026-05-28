from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db import connect, initialize_database, upsert_user
from tokens import (
    TokenFormatError,
    issue_token,
    parse_token_id,
    revoke_token,
    validate_token,
)


def _conn():
    conn = connect(":memory:")
    initialize_database(conn)
    return conn


def test_issue_token_generates_documented_opaque_format_and_stores_no_secret():
    conn = _conn()
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev", display_name="Alice")

    issued = issue_token(conn, user_id=user.id, name="alice-mbp-codex")

    assert issued.token.startswith("aotel_live_tok_")
    assert parse_token_id(issued.token) == issued.record.id
    assert issued.record.id.startswith("tok_")
    assert issued.record.capture_profile == "normal"
    assert issued.record.scopes == "logs,traces,metrics"

    row = conn.execute("SELECT * FROM tokens WHERE id = ?", (issued.record.id,)).fetchone()
    assert row["token_hash"] != issued.token
    assert issued.token not in row["token_hash"]
    assert row["token_prefix"] == issued.token[:24]
    assert row["token_last4"] == issued.token[-4:]


def test_parse_token_id_rejects_malformed_tokens():
    with pytest.raises(TokenFormatError):
        parse_token_id("not-a-token")

    with pytest.raises(TokenFormatError):
        parse_token_id("aotel_live_tok_short_secret")


def test_validate_token_accepts_active_token_and_writes_audit_row():
    conn = _conn()
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")
    issued = issue_token(conn, user_id=user.id)

    result = validate_token(
        conn,
        issued.token,
        path="/v1/logs",
        content_length=123,
        remote_addr="203.0.113.10",
    )

    assert result.ok is True
    assert result.status_code == 204
    assert result.user.email == "alice@example.com"
    assert result.team_id == "quant-dev"
    assert result.token.id == issued.record.id
    assert result.headers == {
        "X-Telemetry-User": "alice@example.com",
        "X-Telemetry-Team": "quant-dev",
        "X-Telemetry-User-Id": user.id,
        "X-Telemetry-Token-Id": issued.record.id,
        "X-Telemetry-Capture-Profile": "normal",
    }

    token_row = conn.execute("SELECT last_seen_at FROM tokens WHERE id = ?", (issued.record.id,)).fetchone()
    assert token_row["last_seen_at"] is not None

    audit = conn.execute("SELECT * FROM ingest_audit").fetchone()
    assert audit["token_id"] == issued.record.id
    assert audit["user_id"] == user.id
    assert audit["team_id"] == "quant-dev"
    assert audit["path"] == "/v1/logs"
    assert audit["content_length"] == 123
    assert audit["status_code"] == 204
    assert audit["remote_addr"] == "203.0.113.10"


def test_validate_token_rejects_hash_mismatch_with_401():
    conn = _conn()
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")
    issued = issue_token(conn, user_id=user.id)
    bad_token = issued.token[:-1] + ("A" if issued.token[-1] != "A" else "B")

    result = validate_token(conn, bad_token, path="/v1/logs")

    assert result.ok is False
    assert result.status_code == 401
    assert result.reason == "hash_mismatch"
    audit = conn.execute("SELECT token_id, status_code FROM ingest_audit").fetchone()
    assert audit["token_id"] == issued.record.id
    assert audit["status_code"] == 401


def test_validate_token_rejects_revoked_expired_disabled_and_scope_mismatch():
    conn = _conn()
    now = datetime(2026, 5, 28, tzinfo=timezone.utc)
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")

    revoked = issue_token(conn, user_id=user.id)
    revoke_token(conn, revoked.record.id, now=now)
    assert validate_token(conn, revoked.token, path="/v1/logs", now=now).reason == "revoked"
    assert validate_token(conn, revoked.token, path="/v1/logs", now=now).status_code == 403

    expired = issue_token(conn, user_id=user.id, expires_at=now - timedelta(seconds=1))
    expired_result = validate_token(conn, expired.token, path="/v1/logs", now=now)
    assert expired_result.reason == "expired"
    assert expired_result.status_code == 403

    scoped = issue_token(conn, user_id=user.id, scopes=("logs",))
    scoped_result = validate_token(conn, scoped.token, path="/v1/traces", now=now)
    assert scoped_result.reason == "scope_not_allowed"
    assert scoped_result.status_code == 403

    disabled_user = upsert_user(conn, email="bob@example.com", team_id="quant-dev")
    disabled = issue_token(conn, user_id=disabled_user.id)
    conn.execute("UPDATE users SET status = 'disabled' WHERE id = ?", (disabled_user.id,))
    disabled_result = validate_token(conn, disabled.token, path="/v1/logs", now=now)
    assert disabled_result.reason == "disabled_user"
    assert disabled_result.status_code == 403


def test_issue_token_supports_max_capture_profile_and_short_scopes():
    conn = _conn()
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")

    issued = issue_token(
        conn,
        user_id=user.id,
        name="alice-forensics",
        scopes=("logs", "traces"),
        capture_profile="max",
    )

    assert issued.record.capture_profile == "max"
    assert issued.record.scopes == "logs,traces"
    result = validate_token(conn, issued.token, path="/v1/traces")
    assert result.ok is True
    assert result.headers["X-Telemetry-Capture-Profile"] == "max"
