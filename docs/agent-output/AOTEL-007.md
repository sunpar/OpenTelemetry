# AOTEL-007 Completion

## Changes

- Added `compose/docker-compose.gateway.yml` for `auth-api`, Nginx, and the OpenTelemetry Collector gateway.
- Published only the authenticated Nginx gateway port to the host.
- Kept auth-api and Collector ingestion on private Docker networks.
- Mounted the repository read-only into `auth-api` so `make user` and `make token` can run `otelctl` in the auth service context against the shared SQLite volume.
- Replaced Makefile placeholders with runnable `signoz-up`, `signoz-down`, `up`, `down`, `logs`, `user`, `token`, `smoke`, `install-codex`, and `install-claude` targets.
- Updated `.env.example` with the SigNoz vendor directory setting.

## Verification

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_aotel007_gateway_compose.py tests/test_aotel001_scaffold.py -q
# 12 passed in 0.11s

docker compose -f compose/docker-compose.gateway.yml config
# rendered agent-otel-gateway with auth-api, nginx, and otel-collector services

PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
# 61 passed, 1 warning in 0.66s

git diff --check
# no output
```

The warning is the existing Starlette/FastAPI TestClient deprecation warning from the test environment.

## Risks And Deviations

- Updated the original scaffold Makefile test because the placeholder assertion became obsolete once the targets were implemented.
- `make signoz-up` follows the documented upstream SigNoz Docker Compose path. The repo still does not vendor or rewrite SigNoz's upstream deployment files.
