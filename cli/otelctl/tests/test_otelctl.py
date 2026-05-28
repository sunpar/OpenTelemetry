from datetime import datetime, timezone
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services/auth-api/src"))

from db import connect
from otelctl import main
from tokens import validate_token


TOKEN_RE = re.compile(r"aotel_live_tok_[0-9A-HJKMNPQRSTVWXYZ]{26}_[A-Za-z0-9_-]+")


def _run(args, capsys, db_path):
    rc = main(["--db-path", str(db_path), *args])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _issued_token(output: str) -> str:
    matches = TOKEN_RE.findall(output)
    assert len(matches) == 1
    return matches[0]


def test_users_add_and_tokens_issue_create_valid_token(tmp_path, capsys):
    db_path = tmp_path / "auth.sqlite3"

    rc, out, err = _run(
        ["users", "add", "--email", "alice@example.com", "--team", "quant-dev", "--name", "Alice"],
        capsys,
        db_path,
    )
    assert rc == 0
    assert err == ""
    assert "alice@example.com" in out

    rc, out, err = _run(
        [
            "tokens",
            "issue",
            "--email",
            "alice@example.com",
            "--name",
            "alice-mbp-codex",
            "--expires",
            "90d",
            "--endpoint",
            "http://localhost:8088",
        ],
        capsys,
        db_path,
    )
    assert rc == 0
    assert err == ""
    token = _issued_token(out)
    assert out.count(token) == 1
    assert "Codex config snippet" in out
    assert "Claude Code env snippet" in out
    assert "<TOKEN>" in out
    assert "raw Claude API body capture is opt-in only" in out

    conn = connect(db_path)
    result = validate_token(conn, token, path="/v1/logs")
    assert result.ok is True
    row = conn.execute("SELECT expires_at FROM tokens WHERE id = ?", (result.token.id,)).fetchone()
    assert datetime.fromisoformat(row["expires_at"]) > datetime.now(timezone.utc)


def test_tokens_list_redacts_token_secret(tmp_path, capsys):
    db_path = tmp_path / "auth.sqlite3"
    _run(["users", "add", "--email", "alice@example.com", "--team", "quant-dev"], capsys, db_path)
    _, issue_out, _ = _run(["tokens", "issue", "--email", "alice@example.com"], capsys, db_path)
    token = _issued_token(issue_out)

    rc, out, err = _run(["tokens", "list", "--email", "alice@example.com"], capsys, db_path)

    assert rc == 0
    assert err == ""
    assert token not in out
    assert token[:24] in out
    assert token[-4:] in out


def test_revoke_and_disable_change_validation_outcomes(tmp_path, capsys):
    db_path = tmp_path / "auth.sqlite3"
    _run(["users", "add", "--email", "alice@example.com", "--team", "quant-dev"], capsys, db_path)
    _, issue_out, _ = _run(["tokens", "issue", "--email", "alice@example.com"], capsys, db_path)
    token = _issued_token(issue_out)

    conn = connect(db_path)
    before = validate_token(conn, token, path="/v1/logs")
    assert before.ok is True

    rc, out, err = _run(["tokens", "revoke", "--token-id", before.token.id], capsys, db_path)
    assert rc == 0
    assert err == ""
    assert before.token.id in out
    assert validate_token(conn, token, path="/v1/logs").reason == "revoked"

    _run(["users", "add", "--email", "bob@example.com", "--team", "quant-dev"], capsys, db_path)
    _, bob_issue, _ = _run(["tokens", "issue", "--email", "bob@example.com"], capsys, db_path)
    bob_token = _issued_token(bob_issue)
    assert validate_token(conn, bob_token, path="/v1/logs").ok is True

    rc, out, err = _run(["users", "disable", "--email", "bob@example.com"], capsys, db_path)
    assert rc == 0
    assert err == ""
    assert "bob@example.com disabled" in out
    assert validate_token(conn, bob_token, path="/v1/logs").reason == "disabled_user"


def test_max_capture_issue_sets_profile(tmp_path, capsys):
    db_path = tmp_path / "auth.sqlite3"
    _run(["users", "add", "--email", "alice@example.com", "--team", "quant-dev"], capsys, db_path)

    _, out, _ = _run(
        [
            "tokens",
            "issue",
            "--email",
            "alice@example.com",
            "--capture-profile",
            "max",
            "--expires",
            "3d",
        ],
        capsys,
        db_path,
    )
    token = _issued_token(out)
    conn = connect(db_path)
    result = validate_token(conn, token, path="/v1/logs")
    assert result.headers["X-Telemetry-Capture-Profile"] == "max"
    assert "--token-capture-profile max" in out
