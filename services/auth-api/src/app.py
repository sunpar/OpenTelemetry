from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, Request, Response

from db import connect, initialize_database
from settings import Settings
from tokens import validate_token


def _content_length(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _original_path(value: str | None) -> str:
    if not value:
        return ""
    return urlsplit(value).path


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        conn = connect(app_settings.auth_db_path)
        try:
            initialize_database(conn)
        finally:
            conn.close()
        yield

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

        original_path = _original_path(x_original_uri)
        remote_addr = x_telemetry_source_ip
        if remote_addr is None and request.client is not None:
            remote_addr = request.client.host

        conn = connect(app_settings.auth_db_path)
        try:
            result = validate_token(
                conn,
                token,
                path=original_path,
                content_length=_content_length(x_original_content_length),
                remote_addr=remote_addr,
            )
        finally:
            conn.close()

        if not result.ok:
            return Response(status_code=result.status_code)

        return Response(status_code=204, headers=result.headers)

    return app


app = create_app()
