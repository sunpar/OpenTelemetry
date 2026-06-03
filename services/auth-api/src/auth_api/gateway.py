from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import httpx
from fastapi import APIRouter, Request, Response
from starlette.responses import PlainTextResponse

from agent_otel_auth_core.db import connect
from agent_otel_auth_core.tokens import validate_token
from auth_api.settings import Settings


OTLP_PATHS = ("/v1/logs", "/v1/traces", "/v1/metrics")
CLIENT_HEADER_ALLOWLIST = ("Content-Type", "Content-Encoding", "Accept", "User-Agent")
RESPONSE_HEADER_ALLOWLIST = ("Content-Type",)


@dataclass(frozen=True)
class ForwardRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes


Forwarder = Callable[[ForwardRequest], Awaitable[tuple[int, Mapping[str, str], bytes]]]


def _content_length(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _source_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


def _upstream_url(settings: Settings, path: str) -> str | None:
    if not settings.otlp_upstream:
        return None
    return f"{settings.otlp_upstream.rstrip('/')}{path}"


def _forward_headers(
    request: Request,
    *,
    trusted_headers: Mapping[str, str],
    source_ip: str | None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name in CLIENT_HEADER_ALLOWLIST:
        value = request.headers.get(name)
        if value:
            headers[name] = value
    headers.update(trusted_headers)
    if source_ip:
        headers["X-Telemetry-Source-Ip"] = source_ip
        headers["X-Forwarded-For"] = source_ip
        headers["X-Real-IP"] = source_ip
    return headers


def _response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    allowed = {name.lower() for name in RESPONSE_HEADER_ALLOWLIST}
    return {name: value for name, value in headers.items() if name.lower() in allowed}


def _default_forwarder(settings: Settings) -> Forwarder:
    async def forward(request: ForwardRequest) -> tuple[int, Mapping[str, str], bytes]:
        async with httpx.AsyncClient(timeout=settings.gateway_forward_timeout_seconds) as client:
            response = await client.request(
                request.method,
                request.url,
                content=request.body,
                headers=request.headers,
            )
        return response.status_code, response.headers, response.content

    return forward


def create_gateway_router(
    *,
    settings: Settings,
    forwarder: Forwarder | None = None,
) -> APIRouter:
    router = APIRouter()
    send = forwarder or _default_forwarder(settings)

    async def handle_otlp(path: str, request: Request) -> Response:
        body = await request.body()
        if len(body) > settings.gateway_max_body_bytes:
            return PlainTextResponse("OTLP payload is too large", status_code=413)

        token = _bearer_token(request)
        if token is None:
            return Response(status_code=401)

        upstream_url = _upstream_url(settings, path)
        if upstream_url is None:
            return PlainTextResponse("OTLP upstream is not configured", status_code=503)

        source_ip = _source_ip(request)
        conn = connect(settings.auth_db_path)
        try:
            result = validate_token(
                conn,
                token,
                path=path,
                content_length=_content_length(request.headers.get("content-length")) or len(body),
                remote_addr=source_ip,
            )
        finally:
            conn.close()

        if not result.ok:
            return Response(status_code=result.status_code)

        try:
            status_code, headers, response_body = await send(
                ForwardRequest(
                    method=request.method,
                    url=upstream_url,
                    headers=_forward_headers(
                        request,
                        trusted_headers=result.headers or {},
                        source_ip=source_ip,
                    ),
                    body=body,
                )
            )
        except httpx.RequestError:
            return PlainTextResponse("OTLP upstream request failed", status_code=502)

        return Response(
            content=response_body,
            status_code=status_code,
            headers=_response_headers(headers),
        )

    @router.post("/v1/logs")
    async def logs(request: Request) -> Response:
        return await handle_otlp("/v1/logs", request)

    @router.post("/v1/traces")
    async def traces(request: Request) -> Response:
        return await handle_otlp("/v1/traces", request)

    @router.post("/v1/metrics")
    async def metrics(request: Request) -> Response:
        return await handle_otlp("/v1/metrics", request)

    return router
