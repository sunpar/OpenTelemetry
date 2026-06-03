# Repo Map

Last updated: 2026-06-02

## Repository Status

This repository contains the local MVP implementation for an authenticated
OpenTelemetry gateway for agent telemetry. The implementation includes runnable
auth-api and `otelctl` Python packages, a native FastAPI OTLP gateway, legacy
Compose reference files, installer scripts, smoke/security scripts, SigNoz
dashboard JSON, and CI.

## Package Manager And Build Files

Current package, build, and validation files:

- `requirements-dev.txt`: editable local package installs plus test/lint tools.
- `Makefile`: local operator targets for the native FastAPI gateway,
  user/token commands, smoke checks, installers, and legacy Compose validation.
- `packages/auth-core/pyproject.toml`: shared auth storage and token package.
- `services/auth-api/pyproject.toml`: FastAPI auth service package.
- `cli/otelctl/pyproject.toml`: operator CLI package.
- `compose/docker-compose.gateway.yml`: legacy auth-api, Nginx, and Collector
  gateway reference.
- `compose/docker-compose.signoz.yml`: SigNoz wrapper metadata.
- `compose/docker-compose.signoz.override.yml`: safe local SigNoz bindings.
- `.github/workflows/ci.yml`: Python and static validation.

## Current File Tree

```text
README.md
.github/
  workflows/
    ci.yml
requirements-dev.txt
Makefile
packages/
  auth-core/
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

- `services/auth-api/`: FastAPI token verification service, native OTLP
  gateway, SQLite runtime settings, and service tests.
- `packages/auth-core/`: shared auth models, SQLite migrations, database
  helpers, and token lifecycle logic.
- `cli/otelctl/`: operator CLI, packaged templates, thin auth compatibility
  wrappers, and CLI tests.
- `infra/nginx/`: legacy Nginx `auth_request` ingress reference for
  `/v1/logs`, `/v1/traces`, and `/v1/metrics`.
- `infra/otel/`: optional native Collector configs and agent normalization
  fragment.
- `infra/signoz/`: SigNoz docs and dashboard JSON.
- `scripts/`: Codex/Claude installers, smoke runner, backup helper, and OTLP
  JSON sender.
- `templates/`: source templates used by installers and CLI snippet output.
- `tests/`: cross-component scaffold, native gateway, legacy Compose,
  installer, script, Collector, Nginx, SigNoz, dashboard, and CI contract tests.

## Entry Points

- `AOTEL_OTLP_UPSTREAM=... make native-up`: start the native FastAPI auth and
  OTLP gateway.
- `make up`: alias for `native-up`.
- `make down`: explain how to stop the foreground native runtime.
- `make user EMAIL=... TEAM=... [NAME=...]`: create/update a telemetry user.
- `make token EMAIL=... [TOKEN_NAME=...] [EXPIRES=90d]`: issue a token and
  print onboarding snippets.
- `make smoke TOKEN=...`: run local gateway smoke/security checks.
- `make install-codex ENDPOINT=... TOKEN=...`: install Codex telemetry config.
- `make install-claude ENDPOINT=... TOKEN=...`: write Claude Code telemetry env.
- `make install-dev`: install local packages and validation tools.
- `make lint`: run Ruff.
- `make test`: run the Python test suite.
- `make static-check`: run docs/static checks plus unstaged and staged git
  whitespace checks.
- `make legacy-compose-config`: validate gateway, SigNoz wrapper, and SigNoz
  upstream override Compose config.
- `make check`: run the root local verification contract.
- `otelctl users add`
- `otelctl users disable`
- `otelctl tokens issue`
- `otelctl tokens list`
- `otelctl tokens revoke`
- `scripts/install-codex-otel.sh`
- `scripts/install-claude-otel.sh`
- `scripts/smoke-test-otel.py`
- `scripts/send-test-log.py`
- `.github/workflows/ci.yml`

## Config Surfaces

- `.env.example`: non-secret local defaults.
- `services/auth-api/src/auth_api/settings.py`: auth-api runtime settings.
- `services/auth-api/src/auth_api/app.py`: packaged FastAPI runtime entrypoint.
- `services/auth-api/src/auth_api/gateway.py`: reusable FastAPI OTLP gateway
  router and upstream forwarding logic.
- `packages/auth-core/src/agent_otel_auth_core/migrations/001_initial.sql`:
  user, token, and ingest audit schema.
- `infra/nginx/nginx.conf`: auth ingress and trusted telemetry headers.
- `infra/otel/collector.local.yaml`: local Collector gateway profile.
- `infra/otel/collector.prod.yaml`: production Collector gateway profile.
- `infra/otel/processors/normalize-agent-fields.yaml`: reusable transform
  processor fragment.
- `templates/codex.config.toml`: managed Codex telemetry block.
- `templates/claude.env`: content-minimal Claude Code telemetry env.
- `templates/claude.max-capture.env`: explicit max-capture overlay.

## Architecture Boundaries

The documented runtime boundary is:

```text
Codex / Claude Code / agent tools
  -> native FastAPI auth-api OTLP gateway
  -> native Collector, managed OTLP endpoint, or separately operated SigNoz
  -> observability backend
```

Trust boundary rules:

- External clients provide only `Authorization`.
- FastAPI gateway overwrites `X-Telemetry-*` identity headers.
- FastAPI gateway derives source IP from the socket or hosting platform.
- Upstream enrichment uses gateway-provided metadata, not client payload fields.
- Backend OTLP ingestion ports stay private.

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
  disabled users, scopes, original URI normalization, and audit rows.
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
- Auth-api still keeps top-level compatibility wrappers (`app`, `settings`,
  `db`, `tokens`, `models`) for local scripts and older tests.
