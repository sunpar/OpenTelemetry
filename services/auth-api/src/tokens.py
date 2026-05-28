from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlsplit

from db import record_ingest_audit, utc_now_iso
from models import IssuedToken, TokenRecord, User, ValidationResult


CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TOKEN_RE = re.compile(
    r"^aotel_live_(tok_[0-9A-HJKMNPQRSTVWXYZ]{26})_([A-Za-z0-9_-]{16,})$"
)
PATH_SCOPES = {
    "/v1/logs": "logs",
    "/v1/traces": "traces",
    "/v1/metrics": "metrics",
}
VALID_SCOPES = frozenset(PATH_SCOPES.values())
TOKEN_ID_RE = re.compile(r"^aotel_live_(tok_[0-9A-HJKMNPQRSTVWXYZ]{26})_")


class TokenFormatError(ValueError):
    pass


def _encode_base32(value: int, length: int) -> str:
    chars: list[str] = []
    for _ in range(length):
        chars.append(CROCKFORD_BASE32[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000)
    randomness = secrets.randbits(80)
    return _encode_base32(timestamp_ms, 10) + _encode_base32(randomness, 16)


def new_token_id() -> str:
    return f"tok_{new_ulid()}"


def parse_token_id(token: str) -> str:
    match = TOKEN_RE.match(token)
    if not match:
        raise TokenFormatError("malformed token")
    return match.group(1)


def _parse_visible_token_id(token: str) -> str | None:
    match = TOKEN_ID_RE.match(token)
    if not match:
        return None
    return match.group(1)


def hash_token(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_path(path: str) -> str:
    return urlsplit(path).path


def _normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for scope in scopes:
        value = scope.strip()
        if "," in value:
            raise ValueError("scope must not contain commas")
        if value not in VALID_SCOPES:
            raise ValueError(f"unsupported scope: {scope}")
        normalized.append(value)
    if not normalized:
        raise ValueError("at least one scope is required")
    return tuple(normalized)


def _token_from_row(row: sqlite3.Row) -> TokenRecord:
    return TokenRecord(
        id=row["token_id"],
        user_id=row["user_id"],
        name=row["name"],
        token_hash=row["token_hash"],
        token_prefix=row["token_prefix"],
        token_last4=row["token_last4"],
        scopes=row["scopes"],
        capture_profile=row["capture_profile"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
        created_at=row["token_created_at"],
        last_seen_at=row["last_seen_at"],
    )


def _user_from_joined_row(row: sqlite3.Row) -> User:
    return User(
        id=row["user_id"],
        email=row["email"],
        display_name=row["display_name"],
        team_id=row["team_id"],
        status=row["status"],
        created_at=row["user_created_at"],
    )


def _lookup_token(conn: sqlite3.Connection, token_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT
          t.id AS token_id,
          t.user_id,
          t.name,
          t.token_hash,
          t.token_prefix,
          t.token_last4,
          t.scopes,
          t.capture_profile,
          t.expires_at,
          t.revoked_at,
          t.created_at AS token_created_at,
          t.last_seen_at,
          u.email,
          u.display_name,
          u.team_id,
          u.status,
          u.created_at AS user_created_at
        FROM tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = ?
        """,
        (token_id,),
    ).fetchone()


def issue_token(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    name: str | None = None,
    scopes: Iterable[str] = ("logs", "traces", "metrics"),
    expires_at: datetime | str | None = None,
    capture_profile: str = "normal",
) -> IssuedToken:
    if capture_profile not in {"normal", "max"}:
        raise ValueError("capture_profile must be normal or max")

    scope_text = ",".join(_normalize_scopes(scopes))

    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise ValueError(f"unknown user_id: {user_id}")

    token_id = new_token_id()
    secret = secrets.token_urlsafe(32)
    token = f"aotel_live_{token_id}_{secret}"
    created_at = utc_now_iso()

    conn.execute(
        """
        INSERT INTO tokens (
          id, user_id, name, token_hash, token_prefix, token_last4, scopes,
          capture_profile, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            token_id,
            user_id,
            name,
            hash_token(token),
            token[:24],
            token[-4:],
            scope_text,
            capture_profile,
            _iso(expires_at),
            created_at,
        ),
    )
    conn.commit()
    row = _lookup_token(conn, token_id)
    return IssuedToken(token=token, record=_token_from_row(row))


def revoke_token(
    conn: sqlite3.Connection,
    token_id: str,
    *,
    now: datetime | None = None,
) -> None:
    conn.execute(
        "UPDATE tokens SET revoked_at = ? WHERE id = ?",
        (_now(now).astimezone(timezone.utc).isoformat(), token_id),
    )
    conn.commit()


def _audit(
    conn: sqlite3.Connection,
    *,
    row: sqlite3.Row | None,
    token_id: str | None,
    path: str | None,
    content_length: int | None,
    status_code: int,
    remote_addr: str | None,
) -> None:
    record_ingest_audit(
        conn,
        token_id=token_id,
        user_id=row["user_id"] if row else None,
        team_id=row["team_id"] if row else None,
        path=path,
        content_length=content_length,
        status_code=status_code,
        remote_addr=remote_addr,
    )


def _reject(
    conn: sqlite3.Connection,
    *,
    reason: str,
    status_code: int,
    row: sqlite3.Row | None,
    token_id: str | None,
    path: str | None,
    content_length: int | None,
    remote_addr: str | None,
) -> ValidationResult:
    _audit(
        conn,
        row=row,
        token_id=token_id,
        path=path,
        content_length=content_length,
        status_code=status_code,
        remote_addr=remote_addr,
    )
    return ValidationResult(ok=False, status_code=status_code, reason=reason)


def validate_token(
    conn: sqlite3.Connection,
    token: str,
    *,
    path: str,
    content_length: int | None = None,
    remote_addr: str | None = None,
    now: datetime | None = None,
) -> ValidationResult:
    normalized_path = _normalize_path(path)
    try:
        token_id = parse_token_id(token)
    except TokenFormatError:
        visible_token_id = _parse_visible_token_id(token)
        if visible_token_id:
            row = _lookup_token(conn, visible_token_id)
            return _reject(
                conn,
                reason="malformed",
                status_code=401,
                row=row,
                token_id=visible_token_id,
                path=normalized_path,
                content_length=content_length,
                remote_addr=remote_addr,
            )
        return ValidationResult(ok=False, status_code=401, reason="malformed")

    row = _lookup_token(conn, token_id)
    if row is None:
        return _reject(
            conn,
            reason="unknown_token",
            status_code=401,
            row=None,
            token_id=token_id,
            path=normalized_path,
            content_length=content_length,
            remote_addr=remote_addr,
        )

    if not hmac.compare_digest(hash_token(token), row["token_hash"]):
        return _reject(
            conn,
            reason="hash_mismatch",
            status_code=401,
            row=row,
            token_id=token_id,
            path=normalized_path,
            content_length=content_length,
            remote_addr=remote_addr,
        )

    if row["revoked_at"]:
        return _reject(
            conn,
            reason="revoked",
            status_code=403,
            row=row,
            token_id=token_id,
            path=normalized_path,
            content_length=content_length,
            remote_addr=remote_addr,
        )

    current_time = _now(now)
    expires_at = _parse_iso(row["expires_at"])
    if expires_at and expires_at <= current_time:
        return _reject(
            conn,
            reason="expired",
            status_code=403,
            row=row,
            token_id=token_id,
            path=normalized_path,
            content_length=content_length,
            remote_addr=remote_addr,
        )

    if row["status"] != "active":
        return _reject(
            conn,
            reason="disabled_user",
            status_code=403,
            row=row,
            token_id=token_id,
            path=normalized_path,
            content_length=content_length,
            remote_addr=remote_addr,
        )

    requested_scope = PATH_SCOPES.get(normalized_path)
    allowed_scopes = {scope.strip() for scope in row["scopes"].split(",") if scope.strip()}
    if requested_scope not in allowed_scopes:
        return _reject(
            conn,
            reason="scope_not_allowed",
            status_code=403,
            row=row,
            token_id=token_id,
            path=normalized_path,
            content_length=content_length,
            remote_addr=remote_addr,
        )

    seen_at = current_time.astimezone(timezone.utc).isoformat()
    conn.execute("UPDATE tokens SET last_seen_at = ? WHERE id = ?", (seen_at, token_id))
    conn.commit()
    _audit(
        conn,
        row=row,
        token_id=token_id,
        path=normalized_path,
        content_length=content_length,
        status_code=204,
        remote_addr=remote_addr,
    )

    token_record = _token_from_row(row)
    user = _user_from_joined_row(row)
    headers = {
        "X-Telemetry-User": user.email,
        "X-Telemetry-Team": user.team_id,
        "X-Telemetry-User-Id": user.id,
        "X-Telemetry-Token-Id": token_record.id,
        "X-Telemetry-Capture-Profile": token_record.capture_profile,
    }
    return ValidationResult(
        ok=True,
        status_code=204,
        reason="ok",
        token=token_record,
        user=user,
        team_id=user.team_id,
        headers=headers,
    )
