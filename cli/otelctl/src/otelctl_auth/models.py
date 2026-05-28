from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    email: str
    display_name: str | None
    team_id: str
    status: str
    created_at: str


@dataclass(frozen=True)
class TokenRecord:
    id: str
    user_id: str
    name: str | None
    token_hash: str
    token_prefix: str
    token_last4: str
    scopes: str
    capture_profile: str
    expires_at: str | None
    revoked_at: str | None
    created_at: str
    last_seen_at: str | None


@dataclass(frozen=True)
class IssuedToken:
    token: str
    record: TokenRecord


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    status_code: int
    reason: str
    token: TokenRecord | None = None
    user: User | None = None
    team_id: str | None = None
    headers: dict[str, str] | None = None
