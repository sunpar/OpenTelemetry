from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request, Response

from agent_otel_auth_core.db import connect, initialize_database
from agent_otel_auth_core.tokens import validate_token
from auth_api.gateway import ManagedHttpForwarder, create_gateway_router
from auth_api.request_parsing import content_length, original_path
from auth_api.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    gateway_forwarder = ManagedHttpForwarder(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        conn = connect(app_settings.auth_db_path)
        try:
            initialize_database(conn)
        finally:
            conn.close()
        await gateway_forwarder.open()
        try:
            yield
        finally:
            await gateway_forwarder.close()

    app = FastAPI(
        title="Agent OpenTelemetry auth-api",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.api_route("/auth/verify", methods=["GET", "POST"])
    def verify(
        request: Request,
        authorization: str | None = Header(default=None),
        x_original_uri: str | None = Header(default=None),
        x_original_content_length: str | None = Header(default=None),
        x_telemetry_source_ip: str | None = Header(default=None),
    ) -> Response:
        if authorization is None or not authorization.startswith("Bearer "):
            return Response(status_code=401)

        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            return Response(status_code=401)

        request_path = original_path(x_original_uri)
        remote_addr = x_telemetry_source_ip
        if remote_addr is None and request.client is not None:
            remote_addr = request.client.host

        conn = connect(app_settings.auth_db_path)
        try:
            result = validate_token(
                conn,
                token,
                path=request_path,
                content_length=content_length(x_original_content_length),
                remote_addr=remote_addr,
            )
        finally:
            conn.close()

        if not result.ok:
            return Response(status_code=result.status_code)

        return Response(status_code=204, headers=result.headers)

    app.include_router(create_gateway_router(settings=app_settings, forwarder=gateway_forwarder))

    return app


app = create_app()
