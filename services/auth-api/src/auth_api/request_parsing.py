from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request


def content_length(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


def source_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def original_path(value: str | None) -> str:
    if not value:
        return ""
    return urlsplit(value).path
