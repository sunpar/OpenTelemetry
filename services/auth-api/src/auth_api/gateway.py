from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import httpx
from fastapi import APIRouter, Request, Response
from starlette.responses import PlainTextResponse

from agent_otel_auth_core.db import connect
from agent_otel_auth_core.tokens import validate_token
from auth_api.request_parsing import bearer_token, content_length, source_ip
from auth_api.settings import Settings


OTLP_PATHS = ("/v1/logs", "/v1/traces", "/v1/metrics")
CLIENT_HEADER_ALLOWLIST = ("Content-Type", "Content-Encoding", "Accept", "User-Agent")
RESPONSE_HEADER_ALLOWLIST = ("Content-Type",)


class PayloadTooLarge(Exception):
    pass


@dataclass(frozen=True)
class ForwardRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes


Forwarder = Callable[[ForwardRequest], Awaitable[tuple[int, Mapping[str, str], bytes]]]


def _upstream_url(settings: Settings, path: str) -> str | None:
    if not settings.otlp_upstream:
        return None
    return f"{settings.otlp_upstream.rstrip('/')}{path}"


def _forward_headers(
    request: Request,
    *,
    trusted_headers: Mapping[str, str],
    source_ip: str | None,
    upstream_authorization: str | None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name in CLIENT_HEADER_ALLOWLIST:
        value = request.headers.get(name)
        if value:
            headers[name] = value
    if upstream_authorization:
        headers["Authorization"] = upstream_authorization
    headers.update(trusted_headers)
    if source_ip:
        headers["X-Telemetry-Source-Ip"] = source_ip
        headers["X-Forwarded-For"] = source_ip
        headers["X-Real-IP"] = source_ip
    return headers


def _response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    allowed = {name.lower() for name in RESPONSE_HEADER_ALLOWLIST}
    return {name: value for name, value in headers.items() if name.lower() in allowed}


async def _send_forward_request(
    client: httpx.AsyncClient,
    request: ForwardRequest,
) -> tuple[int, Mapping[str, str], bytes]:
    response = await client.request(
        request.method,
        request.url,
        content=request.body,
        headers=request.headers,
    )
    return response.status_code, response.headers, response.content


def _default_forwarder(settings: Settings) -> Forwarder:
    async def forward(request: ForwardRequest) -> tuple[int, Mapping[str, str], bytes]:
        async with httpx.AsyncClient(timeout=settings.gateway_forward_timeout_seconds) as client:
            return await _send_forward_request(client, request)

    return forward


async def _read_limited_body(request: Request, *, max_body_bytes: int) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if not chunk:
            continue
        if len(body) + len(chunk) > max_body_bytes:
            raise PayloadTooLarge
        body.extend(chunk)
    return bytes(body)


class ManagedHttpForwarder:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._settings.gateway_forward_timeout_seconds)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __call__(self, request: ForwardRequest) -> tuple[int, Mapping[str, str], bytes]:
        if self._client is None:
            async with httpx.AsyncClient(timeout=self._settings.gateway_forward_timeout_seconds) as client:
                return await _send_forward_request(client, request)
        return await _send_forward_request(self._client, request)


def create_gateway_router(
    *,
    settings: Settings,
    forwarder: Forwarder | None = None,
) -> APIRouter:
    router = APIRouter()
    send = forwarder or _default_forwarder(settings)

    async def handle_otlp(path: str, request: Request) -> Response:
        declared_size = content_length(request.headers.get("content-length"))
        if declared_size is not None and declared_size > settings.gateway_max_body_bytes:
            return PlainTextResponse("OTLP payload is too large", status_code=413)
        try:
            body = await _read_limited_body(request, max_body_bytes=settings.gateway_max_body_bytes)
        except PayloadTooLarge:
            return PlainTextResponse("OTLP payload is too large", status_code=413)

        token = bearer_token(request)
        if token is None:
            return Response(status_code=401)

        upstream_url = _upstream_url(settings, path)
        if upstream_url is None:
            return PlainTextResponse("OTLP upstream is not configured", status_code=503)

        remote_addr = source_ip(request)
        conn = connect(settings.auth_db_path)
        try:
            result = validate_token(
                conn,
                token,
                path=path,
                content_length=declared_size or len(body),
                remote_addr=remote_addr,
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
                        source_ip=remote_addr,
                        upstream_authorization=settings.otlp_upstream_authorization,
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

    def _make_endpoint(path: str):
        # Bind each route's OTLP path so FastAPI cannot expose it as a query parameter.
        async def endpoint(request: Request) -> Response:
            return await handle_otlp(path, request)

        return endpoint

    for otlp_path in OTLP_PATHS:
        router.add_api_route(otlp_path, _make_endpoint(otlp_path), methods=["POST"])

    return router
