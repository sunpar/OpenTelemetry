from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db import connect, initialize_database, record_ingest_audit, upsert_user


def test_schema_contains_required_tables_and_columns():
    conn = connect(":memory:")
    initialize_database(conn)

    expected = {
        "users": {
            "id",
            "email",
            "display_name",
            "team_id",
            "status",
            "created_at",
        },
        "tokens": {
            "id",
            "user_id",
            "name",
            "token_hash",
            "token_prefix",
            "token_last4",
            "scopes",
            "capture_profile",
            "expires_at",
            "revoked_at",
            "created_at",
            "last_seen_at",
        },
        "ingest_audit": {
            "id",
            "token_id",
            "user_id",
            "team_id",
            "path",
            "content_length",
            "status_code",
            "remote_addr",
            "created_at",
        },
    }

    for table, columns in expected.items():
        actual = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        assert columns.issubset(actual)


def test_upsert_user_creates_and_updates_user_without_changing_id():
    conn = connect(":memory:")
    initialize_database(conn)

    created = upsert_user(conn, email="alice@example.com", team_id="quant-dev", display_name="Alice")
    updated = upsert_user(conn, email="alice@example.com", team_id="platform", display_name="Alice Q")

    assert updated.id == created.id
    assert updated.team_id == "platform"
    assert updated.display_name == "Alice Q"
    assert updated.status == "active"


def test_record_ingest_audit_never_requires_or_stores_request_body():
    conn = connect(":memory:")
    initialize_database(conn)

    audit_id = record_ingest_audit(
        conn,
        token_id="tok_01JYABCDEF1234567890ABCD",
        user_id="usr_01JYABCDEF1234567890ABCD",
        team_id="quant-dev",
        path="/v1/logs",
        content_length=42,
        status_code=401,
        remote_addr="203.0.113.10",
    )

    row = conn.execute("SELECT * FROM ingest_audit WHERE id = ?", (audit_id,)).fetchone()
    assert row["path"] == "/v1/logs"
    assert row["content_length"] == 42
    assert "body" not in row.keys()
