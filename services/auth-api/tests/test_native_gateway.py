from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_otel_auth_core.db import connect, initialize_database, upsert_user
from agent_otel_auth_core.tokens import issue_token
from auth_api.gateway import ForwardRequest, create_gateway_router
from auth_api.settings import Settings


def _settings(tmp_path, **overrides):
    db_path = tmp_path / "auth.sqlite3"
    conn = connect(db_path)
    initialize_database(conn)
    values = {
        "auth_db_path": str(db_path),
        "otlp_upstream": "http://collector.example.internal",
    }
    values.update(overrides)
    return Settings(**values), conn


def _client(settings, forwarder):
    app = FastAPI()
    app.include_router(create_gateway_router(settings=settings, forwarder=forwarder))
    return TestClient(app)


def _issue(conn, *, email="alice@example.com", team="quant-dev", capture_profile="normal"):
    user = upsert_user(conn, email=email, team_id=team)
    issued = issue_token(conn, user_id=user.id, capture_profile=capture_profile)
    return user, issued


def test_gateway_rejects_missing_token_without_forwarding(tmp_path):
    settings, conn = _settings(tmp_path)
    forwarded = []

    async def forwarder(request: ForwardRequest):
        forwarded.append(request)
        raise AssertionError("invalid requests must not be forwarded")

    client = _client(settings, forwarder)

    response = client.post("/v1/logs", content=b"{}")

    assert response.status_code == 401
    assert forwarded == []
    assert conn.execute("SELECT COUNT(*) FROM ingest_audit").fetchone()[0] == 0


def test_gateway_requires_configured_upstream(tmp_path):
    settings, conn = _settings(tmp_path, otlp_upstream=None)
    _, issued = _issue(conn)

    async def forwarder(request: ForwardRequest):
        raise AssertionError("requests without an upstream must not be forwarded")

    client = _client(settings, forwarder)

    response = client.post("/v1/logs", headers={"Authorization": f"Bearer {issued.token}"}, content=b"{}")

    assert response.status_code == 503
    assert response.text == "OTLP upstream is not configured"


def test_gateway_rejects_missing_token_before_reporting_missing_upstream(tmp_path):
    settings, _ = _settings(tmp_path, otlp_upstream=None)

    async def forwarder(request: ForwardRequest):
        raise AssertionError("unauthenticated requests must not be forwarded")

    client = _client(settings, forwarder)

    response = client.post("/v1/logs", content=b"{}")

    assert response.status_code == 401


def test_gateway_forwards_valid_otlp_request_with_trusted_headers(tmp_path):
    settings, conn = _settings(tmp_path)
    user, issued = _issue(conn, capture_profile="max")
    forwarded = []

    async def forwarder(request: ForwardRequest):
        forwarded.append(request)
        return 202, {"Content-Type": "application/json"}, b'{"partial_success":{}}'

    client = _client(settings, forwarder)

    response = client.post(
        "/v1/traces",
        headers={
            "Authorization": f"Bearer {issued.token}",
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "gzip",
            "Accept": "application/json",
            "User-Agent": "otel-client/1.0",
            "X-Telemetry-User": "mallory@example.com",
            "X-Telemetry-Team": "spoofed",
            "X-Telemetry-Token-Id": "tok_spoofed",
        },
        content=b"\x1f\x8bpayload",
    )

    assert response.status_code == 202
    assert response.json() == {"partial_success": {}}
    assert len(forwarded) == 1

    forwarded_request = forwarded[0]
    assert forwarded_request.method == "POST"
    assert forwarded_request.url == "http://collector.example.internal/v1/traces"
    assert forwarded_request.body == b"\x1f\x8bpayload"
    assert forwarded_request.headers["Content-Type"] == "application/x-protobuf"
    assert forwarded_request.headers["Content-Encoding"] == "gzip"
    assert forwarded_request.headers["Accept"] == "application/json"
    assert forwarded_request.headers["User-Agent"] == "otel-client/1.0"
    assert forwarded_request.headers["X-Telemetry-User"] == "alice@example.com"
    assert forwarded_request.headers["X-Telemetry-Team"] == "quant-dev"
    assert forwarded_request.headers["X-Telemetry-User-Id"] == user.id
    assert forwarded_request.headers["X-Telemetry-Token-Id"] == issued.record.id
    assert forwarded_request.headers["X-Telemetry-Capture-Profile"] == "max"

    audit = conn.execute("SELECT path, status_code, token_id FROM ingest_audit").fetchone()
    assert audit["path"] == "/v1/traces"
    assert audit["status_code"] == 204
    assert audit["token_id"] == issued.record.id


def test_gateway_rejects_oversized_payload_before_auth_audit(tmp_path):
    settings, conn = _settings(tmp_path, gateway_max_body_bytes=3)
    _, issued = _issue(conn)
    forwarded = []

    async def forwarder(request: ForwardRequest):
        forwarded.append(request)
        raise AssertionError("oversized requests must not be forwarded")

    client = _client(settings, forwarder)

    response = client.post("/v1/metrics", headers={"Authorization": f"Bearer {issued.token}"}, content=b"1234")

    assert response.status_code == 413
    assert response.text == "OTLP payload is too large"
    assert forwarded == []
    assert conn.execute("SELECT COUNT(*) FROM ingest_audit").fetchone()[0] == 0
