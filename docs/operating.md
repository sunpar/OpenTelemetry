# Operating Guide

This guide describes the local and team-trial operations targeted by Milestone 1
and later.

## Local Startup

```sh
make signoz-up
make up
```

Expected services:

- SigNoz UI and storage
- auth-api
- Nginx authenticated ingress
- OpenTelemetry Collector gateway

## Local Shutdown

```sh
make down
```

The gateway stack stops without deleting SigNoz data by default. Destructive
cleanup needs a separate target.

## Logs

```sh
make logs
```

For narrower checks:

```sh
docker compose -f compose/docker-compose.gateway.yml logs -f auth-api
docker compose -f compose/docker-compose.gateway.yml logs -f nginx
docker compose -f compose/docker-compose.gateway.yml logs -f otel-collector
```

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
docker compose -f compose/docker-compose.gateway.yml exec auth-api \
  otelctl tokens revoke --token-id tok_01J...
```

Disable a user:

```sh
docker compose -f compose/docker-compose.gateway.yml exec auth-api \
  otelctl users disable --email alice@example.com
```

## Smoke Tests

Invalid token path:

```sh
curl -i http://localhost:8088/v1/logs \
  -H 'Authorization: Bearer invalid'
```

Valid token path:

```sh
make smoke TOKEN=<issued-token>
```

The smoke target runs:

```sh
python3 scripts/smoke-test-otel.py \
  --endpoint http://localhost:8088 \
  --token <issued-token>
```

It checks:

- invalid bearer tokens return `401` on `/v1/logs`, `/v1/traces`, and
  `/v1/metrics`
- a valid token can send a JSON OTLP test log through Nginx to the Collector
- spoofed `X-Telemetry-*` and `X-Forwarded-For` headers are sent through the
  ingress overwrite path
- host ports `127.0.0.1:4318` and `127.0.0.1:4317` are not reachable as direct
  ingestion paths

To send only one test log:

```sh
python3 scripts/send-test-log.py \
  --endpoint http://localhost:8088 \
  --token <issued-token>
```

SigNoz must show a test log with:

- `telemetry.user.email`
- `telemetry.team.id`
- `telemetry.token.id`
- `agent.tool`

## Health Checks

Gateway health:

```sh
curl -fsS http://localhost:8088/healthz
```

Container health:

```sh
docker compose -f compose/docker-compose.gateway.yml ps
```

Collector health is visible in the Collector health dashboard after dashboard
import only when Collector self-metrics are already routed into SigNoz. The
current gateway Collector configs export client telemetry to SigNoz, but do not
scrape the gateway Collector's own metrics endpoint.

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
- SigNoz ClickHouse volumes
- generated dashboard JSON
- `.env` files that contain endpoints, not tokens

Do not commit issued tokens, populated `.env` files, SQLite databases, or SigNoz
data volumes.

## Production Notes

- Put TLS in front of the gateway.
- Keep auth-api and Collector private.
- Keep SigNoz OTLP ingestion private.
- Add rate limits before opening the endpoint broadly.
- Add backups before onboarding more than a small pilot group.
- Monitor Collector queue size, exporter failures, refused telemetry, memory
  limiter activity, and SigNoz disk growth.

## Operator Questions

- What did a user's Codex do today?
- Which users generated the most telemetry?
- Which tools generated the most telemetry?
- Are Collector exporter queues backing up?
- Are tokens still active after revocation?
- Did max-capture telemetry accidentally stay enabled?
