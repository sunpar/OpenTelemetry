from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import User


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.executescript(migration.read_text())
    conn.commit()


def _new_user_id() -> str:
    return f"usr_{uuid.uuid4().hex[:26]}"


def _user_from_row(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        team_id=row["team_id"],
        status=row["status"],
        created_at=row["created_at"],
    )


def upsert_user(
    conn: sqlite3.Connection,
    *,
    email: str,
    team_id: str,
    display_name: str | None = None,
    status: str = "active",
) -> User:
    existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE users
            SET display_name = ?, team_id = ?, status = ?
            WHERE email = ?
            """,
            (display_name, team_id, status, email),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return _user_from_row(row)

    user_id = _new_user_id()
    created_at = utc_now_iso()
    conn.execute(
        """
        INSERT INTO users (id, email, display_name, team_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, email, display_name, team_id, status, created_at),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_from_row(row)


def record_ingest_audit(
    conn: sqlite3.Connection,
    *,
    token_id: str | None,
    user_id: str | None,
    team_id: str | None,
    path: str | None,
    content_length: int | None,
    status_code: int,
    remote_addr: str | None,
    created_at: str | None = None,
) -> int:
    timestamp = created_at or utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO ingest_audit (
          token_id, user_id, team_id, path, content_length, status_code,
          remote_addr, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            token_id,
            user_id,
            team_id,
            path,
            content_length,
            status_code,
            remote_addr,
            timestamp,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)
