# Agent OpenTelemetry Trial

This repository defines an internal telemetry product for Codex, Claude Code,
and other agent tools. It includes an authenticated OTLP ingress, a
token/control-plane service, an OpenTelemetry Collector gateway, client
onboarding generators, SigNoz bootstrap material, and a starter dashboard set.

## Target Outcome

Agent tools send OTLP/HTTP telemetry to one company endpoint:

```text
POST https://otel.yourcompany.com/v1/logs
POST https://otel.yourcompany.com/v1/traces
POST https://otel.yourcompany.com/v1/metrics
Authorization: Bearer <per-user-token>
```

The native FastAPI gateway authenticates each request, overwrites any spoofed
client identity headers with trusted token metadata, and forwards OTLP/HTTP to a
configured upstream collector or observability backend. Every event, span, and
metric can be attributed by user, team, token, and tool without running Docker
as part of this repository's runtime.

## Planned Developer Path

Milestone 1 target local trial path:

```sh
make install-dev PYTHON=.venv/bin/python
AOTEL_OTLP_UPSTREAM=http://127.0.0.1:4318 make native-up PYTHON=.venv/bin/python
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
make smoke TOKEN=<issued-token>
```

`AOTEL_OTLP_UPSTREAM` must be the base URL of a native OpenTelemetry Collector,
managed OTLP/HTTP endpoint, or separately operated SigNoz ingest endpoint. Do
not include `/v1/logs`, `/v1/traces`, or `/v1/metrics`; the gateway appends the
signal path before forwarding. If the upstream backend requires ingestion
credentials, set `AOTEL_OTLP_UPSTREAM_AUTHORIZATION` to the backend
`Authorization` header value; user bearer tokens are authenticated by the
gateway and are not forwarded upstream. This repository no longer requires
Docker images for its runtime.

The token command prints Codex and Claude Code snippets so teammates do not have
to assemble OpenTelemetry settings by hand.

## Documentation

- [Architecture](docs/architecture.md)
- [Onboarding](docs/onboarding.md)
- [Token Model](docs/token-model.md)
- [Data Model](docs/data-model.md)
- [Codex Telemetry Storage Map](docs/codex-telemetry-storage.md)
- [Operating Guide](docs/operating.md)
- [Storage and Retention](docs/storage-retention.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Milestones](docs/milestones.md)

## Planned Repository Shape

```text
agent-otel-trial/
  README.md
  Makefile
  justfile
  .env.example
  compose/
    docker-compose.gateway.yml        # legacy reference only
    docker-compose.signoz.yml         # legacy reference only
  infra/
    nginx/
      nginx.conf
    otel/
      collector.local.yaml
      collector.prod.yaml
      processors/
        normalize-agent-fields.yaml
    signoz/
      README.md
      dashboards/
        codex-overview.json
        claude-overview.json
        team-usage.json
        collector-health.json
  services/
    auth-api/
      pyproject.toml
      Dockerfile
      src/
        app.py
        db.py
        tokens.py
        models.py
        settings.py
        auth_api/
          app.py
          settings.py
      tests/
  packages/
    auth-core/
      pyproject.toml
      src/
        agent_otel_auth_core/
          db.py
          tokens.py
          models.py
          migrations/
  cli/
    otelctl/
      pyproject.toml
      src/
        otelctl.py
  scripts/
    install-codex-otel.sh
    install-claude-otel.sh
    smoke-test-otel.py
    send-test-log.py
    backup-codex-config.sh
  templates/
    codex.config.toml
    claude.env
    claude.max-capture.env
  docs/
    architecture.md
    onboarding.md
    token-model.md
    data-model.md
    operating.md
    storage-retention.md
    troubleshooting.md
    milestones.md
```

## Current Status

This repository contains a native FastAPI auth and OTLP gateway runtime,
operator CLI, onboarding installers, dashboard/query references, and legacy
Compose files retained for comparison. The default build, test, and runtime
paths do not require Docker.
