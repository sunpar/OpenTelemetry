# Repo Map

Last updated: 2026-05-28

## Repository Status

This repository is currently documentation-only. It defines the implementation
contract for an authenticated OpenTelemetry gateway for agent telemetry, but it
does not yet contain runnable services, Compose files, installers, dashboards,
tests, CI, or package manager metadata.

## Package Manager And Build Files

No package manager or build files exist yet.

Absent files checked:

- `package.json`
- `pyproject.toml`
- `requirements.txt`
- `go.mod`
- `Cargo.toml`
- `Makefile`
- `justfile`
- `docker-compose*.yml`
- `.github/workflows/*`

## Current File Tree

```text
README.md
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

## Planned Source Boundaries

The planned implementation shape is documented in `README.md` and
`docs/milestones.md`. These directories do not exist yet:

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

No executable entry points exist in the current tree.

Planned entry points:

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

## Config Surfaces

Current config exists only as documentation snippets.

Planned config files:

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

- Final service language and packaging are not implemented.
- Build, lint, and test commands are documentation-only until package manager
  files and source directories exist.
- No auth-api DB migration strategy exists yet.
- No Compose network topology exists yet.
- No dashboard JSON exists yet.
- No SigNoz bootstrap mechanism exists yet.
- No CI provider or workflow exists yet.
- Codex telemetry config must be re-verified against the installed Codex CLI
  before shipping the installer.
