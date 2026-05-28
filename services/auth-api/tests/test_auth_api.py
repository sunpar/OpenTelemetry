from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import auth_api.app as app_module
from auth_api.app import create_app
from db import connect, initialize_database, upsert_user
from auth_api.settings import Settings
from tokens import issue_token, new_token_id, revoke_token


def _client(tmp_path):
    db_path = tmp_path / "auth.sqlite3"
    conn = connect(db_path)
    initialize_database(conn)
    settings = Settings(auth_db_path=str(db_path))
    client = TestClient(create_app(settings=settings))
    return client, conn


def _headers(token: str, path: str = "/v1/logs"):
    return {
        "Authorization": f"Bearer {token}",
        "X-Original-URI": path,
        "X-Original-Content-Length": "123",
        "X-Telemetry-Source-Ip": "203.0.113.10",
    }


def test_verify_missing_malformed_and_unknown_tokens_return_401(tmp_path):
    client, conn = _client(tmp_path)

    assert client.get("/auth/verify").status_code == 401
    assert client.get("/auth/verify", headers={"Authorization": "Bearer invalid"}).status_code == 401

    unknown_token = f"aotel_live_{new_token_id()}_aaaaaaaaaaaaaaaa"
    response = client.get("/auth/verify", headers=_headers(unknown_token))
    assert response.status_code == 401

    audit = conn.execute("SELECT token_id, path, status_code FROM ingest_audit").fetchone()
    assert audit["token_id"] == unknown_token.split("_aaaaaaaaaaaaaaaa")[0].removeprefix("aotel_live_")
    assert audit["path"] == "/v1/logs"
    assert audit["status_code"] == 401


def test_verify_revoked_expired_and_disabled_tokens_return_403(tmp_path):
    client, conn = _client(tmp_path)
    now = datetime.now(timezone.utc)
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")

    revoked = issue_token(conn, user_id=user.id)
    revoke_token(conn, revoked.record.id, now=now)
    assert client.get("/auth/verify", headers=_headers(revoked.token)).status_code == 403

    expired = issue_token(conn, user_id=user.id, expires_at=now - timedelta(seconds=1))
    assert client.get("/auth/verify", headers=_headers(expired.token)).status_code == 403

    disabled_user = upsert_user(conn, email="bob@example.com", team_id="quant-dev")
    disabled = issue_token(conn, user_id=disabled_user.id)
    conn.execute("UPDATE users SET status = 'disabled' WHERE id = ?", (disabled_user.id,))
    conn.commit()
    assert client.get("/auth/verify", headers=_headers(disabled.token)).status_code == 403


def test_verify_valid_token_returns_trusted_headers_and_audits_original_request(tmp_path):
    client, conn = _client(tmp_path)
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")
    issued = issue_token(conn, user_id=user.id, capture_profile="max")

    response = client.get("/auth/verify", headers=_headers(issued.token, path="/v1/traces?ignored=true"))

    assert response.status_code == 204
    assert response.headers["x-telemetry-user"] == "alice@example.com"
    assert response.headers["x-telemetry-team"] == "quant-dev"
    assert response.headers["x-telemetry-user-id"] == user.id
    assert response.headers["x-telemetry-token-id"] == issued.record.id
    assert response.headers["x-telemetry-capture-profile"] == "max"
    assert response.content == b""

    audit = conn.execute("SELECT * FROM ingest_audit WHERE status_code = 204").fetchone()
    assert audit["path"] == "/v1/traces"
    assert audit["content_length"] == 123
    assert audit["remote_addr"] == "203.0.113.10"
    assert audit["token_id"] == issued.record.id


def test_verify_uses_scope_from_original_uri(tmp_path):
    client, conn = _client(tmp_path)
    user = upsert_user(conn, email="alice@example.com", team_id="quant-dev")
    issued = issue_token(conn, user_id=user.id, scopes=("logs",))

    response = client.get("/auth/verify", headers=_headers(issued.token, path="/v1/metrics"))

    assert response.status_code == 403
    audit = conn.execute("SELECT path, status_code FROM ingest_audit ORDER BY id DESC LIMIT 1").fetchone()
    assert audit["path"] == "/v1/metrics"
    assert audit["status_code"] == 403


def test_auth_api_does_not_expose_public_admin_routes(tmp_path):
    client, _ = _client(tmp_path)

    assert client.post("/users").status_code == 404
    assert client.post("/tokens").status_code == 404


def test_verify_initializes_database_on_startup_not_per_request(tmp_path, monkeypatch):
    db_path = tmp_path / "auth.sqlite3"
    calls = []
    real_initialize_database = app_module.initialize_database

    def counting_initialize_database(conn):
        calls.append(True)
        real_initialize_database(conn)

    monkeypatch.setattr(app_module, "initialize_database", counting_initialize_database)
    settings = Settings(auth_db_path=str(db_path))
    unknown_token = f"aotel_live_{new_token_id()}_aaaaaaaaaaaaaaaa"

    with TestClient(create_app(settings=settings)) as client:
        assert len(calls) == 1

        response = client.get("/auth/verify", headers=_headers(unknown_token))

        assert response.status_code == 401
        assert len(calls) == 1
