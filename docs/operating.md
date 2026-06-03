# Operating Guide

This guide describes the native local and team-trial operations for the
FastAPI auth and OTLP gateway runtime.

## Local Startup

```sh
AOTEL_OTLP_UPSTREAM=http://127.0.0.1:4318 make native-up
```

Expected runtime:

- FastAPI `auth-api` serving `/healthz`, `/auth/verify`, `/v1/logs`,
  `/v1/traces`, and `/v1/metrics`
- SQLite auth database at `AUTH_API_DB_PATH`
- native or externally operated OTLP/HTTP upstream base URL at
  `AOTEL_OTLP_UPSTREAM`

## Local Shutdown

```sh
make down
```

The native FastAPI gateway runs in the foreground by default. Stop it with
Ctrl-C or the process supervisor managing it.

## Logs

Foreground logs are printed by `make native-up`. For production, use the logs
from the host process supervisor that starts Uvicorn or the parent FastAPI app.

## User and Token Operations

Create or update a user:

```sh
make user EMAIL=alice@example.com TEAM=quant-dev
```

Issue a token:

```sh
make token EMAIL=alice@example.com
```

Revoke a token:

```sh
PYTHONPATH=packages/auth-core/src:cli/otelctl/src \
  .venv/bin/python cli/otelctl/src/otelctl.py \
  --db-path ./auth-api.sqlite3 tokens revoke --token-id tok_01J...
```

Disable a user:

```sh
PYTHONPATH=packages/auth-core/src:cli/otelctl/src \
  .venv/bin/python cli/otelctl/src/otelctl.py \
  --db-path ./auth-api.sqlite3 users disable --email alice@example.com
```

## Smoke Tests

Invalid token path:

```sh
curl -i http://localhost:8088/v1/logs \
  -H 'Authorization: Bearer invalid'
```

Valid token path:

```sh
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
```

The smoke target runs:

```sh
AOTEL_SMOKE_TOKEN=<issued-token> \
  .venv/bin/python scripts/smoke-test-otel.py --endpoint http://localhost:8088
```

It checks:

- invalid bearer tokens return `401` on `/v1/logs`, `/v1/traces`, and
  `/v1/metrics`
- a valid token can send JSON OTLP test logs, traces, and metrics through the
  FastAPI gateway to the configured upstream
- spoofed `X-Telemetry-*` and `X-Forwarded-For` headers are included on the log
  smoke request so the upstream can be checked for trusted metadata

To send only one test log:

```sh
python3 scripts/send-test-log.py \
  --endpoint http://localhost:8088 \
  --token <issued-token>
```

For real issued tokens, prefer `AOTEL_SMOKE_TOKEN`, `--token-file`, or
`--token-stdin` with `scripts/smoke-test-otel.py` so the token is not exposed in
process listings or shell history.

The configured backend should show a test log with:

- `telemetry.user.email`
- `telemetry.team.id`
- `telemetry.token.id`
- `agent.tool`

## Health Checks

Gateway health:

```sh
curl -fsS http://localhost:8088/healthz
```

If a native Collector is used, check it with the host service manager or its
own telemetry endpoint. The FastAPI gateway itself does not require a Collector
process when `AOTEL_OTLP_UPSTREAM` points directly at a managed backend.
`AOTEL_OTLP_UPSTREAM` must be a base URL; the gateway appends `/v1/logs`,
`/v1/traces`, or `/v1/metrics` for each request.

## Dashboard Import

Dashboard JSON files live under:

```text
infra/signoz/dashboards/
```

Initial files:

- `codex-overview.json`
- `claude-overview.json`
- `team-usage.json`
- `collector-health.json`

Dashboard import docs live in `infra/signoz/README.md` once the first dashboard
JSON exists.

## Backup and Restore

For the local trial, preserve:

- auth-api SQLite DB
- backend storage, if the selected backend is self-hosted
- generated dashboard JSON
- `.env` files that contain endpoints, not tokens

Do not commit issued tokens, populated `.env` files, SQLite databases, or SigNoz
data volumes.

## Production Notes

- Put TLS in front of the gateway.
- Keep backend OTLP ingestion private.
- Add rate limits before opening the endpoint broadly.
- Add backups before onboarding more than a small pilot group.
- Monitor upstream failures, refused telemetry, request volume, latency, and
  backend disk or quota growth.

## Operator Questions

- What did a user's Codex do today?
- Which users generated the most telemetry?
- Which tools generated the most telemetry?
- Are Collector exporter queues backing up?
- Are tokens still active after revocation?
- Did max-capture telemetry accidentally stay enabled?
