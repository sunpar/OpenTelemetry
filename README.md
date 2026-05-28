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

The gateway authenticates each request, injects trusted identity headers, copies
those headers into OpenTelemetry resource attributes, normalizes agent fields,
and exports the result to SigNoz. Every event, span, and metric is tagged by
user, team, token, and tool.

## Planned Developer Path

Milestone 1 target local trial path:

```sh
make signoz-up
make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
make smoke TOKEN=<issued-token>
```

The token command prints Codex and Claude Code snippets so teammates do not have
to assemble OpenTelemetry settings by hand.

## Documentation

- [Architecture](docs/architecture.md)
- [Onboarding](docs/onboarding.md)
- [Token Model](docs/token-model.md)
- [Data Model](docs/data-model.md)
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
    docker-compose.gateway.yml
    docker-compose.signoz.yml
    docker-compose.warehouse.yml
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
      migrations/
      tests/
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

This repository contains the documentation and implementation contract. The next
step is Milestone 1: local end-to-end ingestion with SigNoz, auth-api, Nginx
auth ingress, OpenTelemetry Collector, and a smoke test.
