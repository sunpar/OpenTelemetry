from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _add_auth_api_src_to_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    auth_src = repo_root / "services/auth-api/src"
    if auth_src.exists():
        sys.path.insert(0, str(auth_src))
    return repo_root


REPO_ROOT = _add_auth_api_src_to_path()

from db import connect, initialize_database, upsert_user  # noqa: E402
from tokens import issue_token, revoke_token  # noqa: E402


DEFAULT_DB_PATH = "auth-api.sqlite3"


def _open_db(path: str):
    conn = connect(path)
    initialize_database(conn)
    return conn


def _parse_duration(value: str) -> datetime:
    match = re.fullmatch(r"(\d+)([dhm])", value)
    if not match:
        raise argparse.ArgumentTypeError("duration must look like 90d, 12h, or 30m")
    amount = int(match.group(1))
    unit = match.group(2)
    delta = {
        "d": timedelta(days=amount),
        "h": timedelta(hours=amount),
        "m": timedelta(minutes=amount),
    }[unit]
    return datetime.now(timezone.utc) + delta


def _render_template(path: Path, *, endpoint: str, token: str, log_user_prompt: str = "false") -> str:
    return (
        path.read_text()
        .replace("{{ENDPOINT}}", endpoint.rstrip("/"))
        .replace("{{TOKEN}}", token)
        .replace("{{LOG_USER_PROMPT}}", log_user_prompt)
    )


def _token_issue(args: argparse.Namespace) -> int:
    conn = _open_db(args.db_path)
    user = conn.execute("SELECT * FROM users WHERE email = ?", (args.email,)).fetchone()
    if user is None:
        print(f"unknown user: {args.email}", file=sys.stderr)
        return 1

    issued = issue_token(
        conn,
        user_id=user["id"],
        name=args.name,
        expires_at=args.expires,
        capture_profile=args.capture_profile,
    )
    endpoint = args.endpoint.rstrip("/")
    codex = _render_template(
        REPO_ROOT / "templates/codex.config.toml",
        endpoint=endpoint,
        token="<TOKEN>",
        log_user_prompt="false",
    )
    claude = _render_template(
        REPO_ROOT / "templates/claude.env",
        endpoint=endpoint,
        token="<TOKEN>",
    )

    print(f"Issued token: {issued.token}")
    print(f"Token id: {issued.record.id}")
    print(f"Capture profile: {issued.record.capture_profile}")
    print()
    print("Codex config snippet:")
    print(codex.rstrip())
    print()
    print("Claude Code env snippet:")
    print(claude.rstrip())
    if issued.record.capture_profile == "max":
        print()
        print("For Claude max capture, run install-claude-otel.sh with --profile max --token-capture-profile max.")
    print()
    print("Reminder: raw Claude API body capture is opt-in only.")
    return 0


def _token_list(args: argparse.Namespace) -> int:
    conn = _open_db(args.db_path)
    rows = conn.execute(
        """
        SELECT t.id, t.name, t.token_prefix, t.token_last4, t.scopes,
               t.capture_profile, t.expires_at, t.revoked_at, t.last_seen_at
        FROM tokens t
        JOIN users u ON u.id = t.user_id
        WHERE u.email = ?
        ORDER BY t.created_at DESC
        """,
        (args.email,),
    ).fetchall()
    if not rows:
        print(f"no tokens for {args.email}")
        return 0

    for row in rows:
        status = "revoked" if row["revoked_at"] else "active"
        print(
            f"{row['id']} {status} {row['capture_profile']} "
            f"{row['token_prefix']}...{row['token_last4']} "
            f"scopes={row['scopes']} name={row['name'] or '-'}"
        )
    return 0


def _token_revoke(args: argparse.Namespace) -> int:
    conn = _open_db(args.db_path)
    existing = conn.execute("SELECT id FROM tokens WHERE id = ?", (args.token_id,)).fetchone()
    if existing is None:
        print(f"unknown token id: {args.token_id}", file=sys.stderr)
        return 1
    revoke_token(conn, args.token_id)
    print(f"{args.token_id} revoked")
    return 0


def _users_add(args: argparse.Namespace) -> int:
    conn = _open_db(args.db_path)
    user = upsert_user(
        conn,
        email=args.email,
        team_id=args.team,
        display_name=args.name,
    )
    print(f"{user.email} active team={user.team_id} id={user.id}")
    return 0


def _users_disable(args: argparse.Namespace) -> int:
    conn = _open_db(args.db_path)
    cursor = conn.execute(
        "UPDATE users SET status = 'disabled' WHERE email = ?",
        (args.email,),
    )
    conn.commit()
    if cursor.rowcount == 0:
        print(f"unknown user: {args.email}", file=sys.stderr)
        return 1
    print(f"{args.email} disabled")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="otelctl")
    parser.add_argument(
        "--db-path",
        default=os.environ.get("AUTH_API_DB_PATH", DEFAULT_DB_PATH),
        help="SQLite auth database path",
    )

    subcommands = parser.add_subparsers(dest="resource", required=True)

    users = subcommands.add_parser("users")
    user_commands = users.add_subparsers(dest="command", required=True)

    users_add = user_commands.add_parser("add")
    users_add.add_argument("--email", required=True)
    users_add.add_argument("--team", required=True)
    users_add.add_argument("--name")
    users_add.set_defaults(func=_users_add)

    users_disable = user_commands.add_parser("disable")
    users_disable.add_argument("--email", required=True)
    users_disable.set_defaults(func=_users_disable)

    tokens = subcommands.add_parser("tokens")
    token_commands = tokens.add_subparsers(dest="command", required=True)

    tokens_issue = token_commands.add_parser("issue")
    tokens_issue.add_argument("--email", required=True)
    tokens_issue.add_argument("--name")
    tokens_issue.add_argument("--expires", type=_parse_duration)
    tokens_issue.add_argument("--capture-profile", choices=["normal", "max"], default="normal")
    tokens_issue.add_argument(
        "--endpoint",
        default=os.environ.get("AOTEL_PUBLIC_ENDPOINT", "https://otel.yourcompany.com"),
    )
    tokens_issue.set_defaults(func=_token_issue)

    tokens_list = token_commands.add_parser("list")
    tokens_list.add_argument("--email", required=True)
    tokens_list.set_defaults(func=_token_list)

    tokens_revoke = token_commands.add_parser("revoke")
    tokens_revoke.add_argument("--token-id", required=True)
    tokens_revoke.set_defaults(func=_token_revoke)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
