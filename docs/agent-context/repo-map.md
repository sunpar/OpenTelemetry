# Repo Map

Last updated: 2026-05-28

## Repository Status

This repository now contains the local MVP implementation for an authenticated
OpenTelemetry gateway for agent telemetry. The implementation includes runnable
auth-api and `otelctl` Python packages, Compose contracts, ingress and Collector
configs, installer scripts, smoke/security scripts, SigNoz dashboard JSON, and
CI.

## Package Manager And Build Files

Current package, build, and validation files:

- `requirements-dev.txt`
- `Makefile`
- `pyproject.toml`
- `docker-compose*.yml`
- `.github/workflows/*`

## Current File Tree

```text
README.md
.github/
  workflows/
    ci.yml
requirements-dev.txt
Makefile
compose/
  docker-compose.gateway.yml
  docker-compose.signoz.yml
  docker-compose.signoz.override.yml
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
services/
  auth-api/
cli/
  otelctl/
scripts/
templates/
tests/
docs/
  architecture.md
  data-model.md
  milestones.md
  onboarding.md
  operating.md
  storage-retention.md
  token-model.md
  troubleshooting.md
  agent-context/
    architecture-index.md
    repo-map.md
    test-commands.md
```

## Source Boundaries

The implementation shape is documented in `README.md` and
`docs/milestones.md`:

- `compose/`: Docker Compose entry points for gateway, SigNoz, and optional
  warehouse profile.
- `infra/nginx/`: authenticated OTLP ingress config.
- `infra/otel/`: OpenTelemetry Collector gateway configs and processors.
- `infra/signoz/`: SigNoz bootstrap docs and dashboard JSON.
- `services/auth-api/`: token/control-plane service.
- `cli/otelctl/`: local control-plane CLI.
- `scripts/`: installers, smoke tests, test telemetry senders, and config backup
  helpers.
- `templates/`: generated Codex and Claude Code config templates.

## Entry Points

- `make signoz-up`: start SigNoz for local trial.
- `make up`: start auth-api, Nginx ingress, and Collector gateway.
- `make user EMAIL=... TEAM=...`: create or update a user.
- `make token EMAIL=...`: issue a per-user opaque token and print client
  snippets.
- `make smoke TOKEN=...`: send authenticated test telemetry through the gateway.
- `otelctl users add`
- `otelctl tokens issue`
- `otelctl tokens list`
- `otelctl tokens revoke`
- `otelctl users disable`
- `scripts/install-codex-otel.sh`
- `scripts/install-claude-otel.sh`
- `scripts/smoke-test-otel.py`
- `scripts/send-test-log.py`
- `.github/workflows/ci.yml`

## Config Surfaces

- `infra/nginx/nginx.conf`: `auth_request` ingress for `/v1/logs`,
  `/v1/traces`, and `/v1/metrics`.
- `infra/otel/collector.local.yaml`: OTLP/HTTP receiver with metadata
  enrichment, batching, retry, and SigNoz export.
- `infra/otel/collector.prod.yaml`: production Collector gateway profile.
- `templates/codex.config.toml`: content-minimal Codex OTel config.
- `templates/claude.env`: content-minimal Claude Code OTel env.
- `templates/claude.max-capture.env`: explicit max-capture env overlay.
- `.env.example`: non-secret local defaults.

## Architecture Boundaries

The documented runtime boundary is:

```text
Codex / Claude Code / agent tools
  -> authenticated Nginx or Caddy OTLP ingress
  -> auth-api token verification
  -> OpenTelemetry Collector gateway enrichment and batching
  -> SigNoz backend
```

Trust boundary rules:

- External clients provide only `Authorization`.
- Ingress overwrites `X-Telemetry-*` identity headers.
- Ingress derives source IP from the socket or trusted proxy chain.
- Collector enrichment uses ingress-provided metadata, not client payload fields.
- SigNoz OTLP ingestion ports stay internal.

## Data Model Hotspots

Primary identity and tenancy attributes:

- `telemetry.team.id`
- `telemetry.user.id`
- `telemetry.user.email`
- `telemetry.token.id`
- `telemetry.source.ip`
- `agent.tool`
- `agent.capture.profile`

Cardinality-sensitive fields:

- `agent.session.id`
- `agent.conversation.id`
- `repo.remote`
- `git.branch`
- command strings
- file paths
- raw API body events

## Risk Hotspots

- Token validation: opaque-token parsing, hash comparison, revocation, expiry,
  disabled users, scopes, and audit rows.
- Header trust: spoofed `X-Telemetry-*` headers and source-IP spoofing.
- Direct ingestion exposure: Collector and SigNoz OTLP ports must not be
  externally published.
- Client config generation: Codex TOML and Claude env files must remain
  parseable and content-minimal by default.
- Capture profile: max capture must be explicit, short-lived, and traceable to a
  token.
- Collector resilience: memory limiter, batch processor, sending queue, retry,
  and exporter health metrics.
- Storage growth: raw body capture, high-cardinality metric dimensions, and
  SigNoz retention.

## Known Unknowns

- Live end-to-end ingestion through SigNoz still needs to be run on a real
  local stack.
- Dashboard JSON has not been imported into a live SigNoz instance.
- The Collector config has not been validated with the Collector binary.
- Production TLS termination and deployment environment are not selected.
- SQLite is the v1 persistence layer; Postgres migration remains future work.
- Codex telemetry config must be re-verified against the installed Codex CLI
  before shipping the installer.
