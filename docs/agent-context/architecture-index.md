# Architecture Index

Last updated: 2026-05-28

## Canonical Docs

- `README.md`: repository purpose, target outcome, developer path, and tree.
- `docs/architecture.md`: gateway data flow, trust boundaries, local ports, and
  baseline Collector config.
- `docs/token-model.md`: opaque token format, SQLite schema, validation flow,
  auth headers, CLI contract, status codes, and audit rows.
- `docs/data-model.md`: resource attributes, signal guidance, cardinality
  policy, capture profiles, dashboard dimensions, and normalization rule.
- `docs/onboarding.md`: Codex and Claude Code client config, installers,
  max-capture overlay, and onboarding verification.
- `docs/operating.md`: target local operations, smoke tests, health checks,
  backup/restore, and production notes.
- `docs/storage-retention.md`: SigNoz retention, storage guardrails, optional
  warehouse profile, and S3 archive deferral.
- `docs/troubleshooting.md`: auth failures, routing failures, enrichment
  failures, SigNoz visibility, client telemetry, volume growth, and revocation.
- `docs/milestones.md`: incremental deliverables and acceptance criteria.

## Package And Test Status

The repository has Python package metadata for `auth-api` and `otelctl`, a
root `requirements-dev.txt`, Docker Compose contracts, pytest coverage, Ruff
linting, static validation scripts, and GitHub Actions CI. See
`test-commands.md` for current local and CI verification commands.

## Runtime Boundaries

### Client Tools

Supported initial clients:

- Codex
- Claude Code
- other custom agent tools

Contract:

- send OTLP/HTTP to `/v1/logs`, `/v1/traces`, and `/v1/metrics`
- include only `Authorization: Bearer <token>` as identity input
- normal onboarding is content-minimal
- max capture is opt-in and token-scoped

### Authenticated Ingress

Files:

- `infra/nginx/nginx.conf`
- optional Caddy alternative later

Contract:

- accept only `/v1/logs`, `/v1/traces`, and `/v1/metrics`
- call `auth-api` using subrequest auth
- preserve OTLP payload bodies
- overwrite spoofed `X-Telemetry-*` headers
- derive `X-Telemetry-Source-Ip` from socket or trusted proxy chain
- keep Collector and SigNoz ingestion ports internal

### auth-api

Files:

- `services/auth-api/src/app.py`
- `services/auth-api/src/db.py`
- `services/auth-api/src/tokens.py`
- `services/auth-api/src/models.py`
- `services/auth-api/src/settings.py`
- `services/auth-api/src/auth_api/app.py`
- `services/auth-api/src/auth_api/settings.py`
- `services/auth-api/tests/`
- `packages/auth-core/src/agent_otel_auth_core/`

Contract:

- FastAPI and SQLite for v1
- opaque tokens, not JWTs
- hashed token secrets only
- current identity resolved at request time
- revocation, expiry, disabled-user, and scope checks
- ingest audit rows without request bodies

### otelctl CLI

Files:

- `cli/otelctl/src/otelctl.py`

Contract:

- user creation/update
- token issuance/list/revocation
- user disable
- token issuance prints Codex and Claude Code snippets
- no public admin UI in v1

### OpenTelemetry Collector Gateway

Files:

- `infra/otel/collector.local.yaml`
- `infra/otel/collector.prod.yaml`
- `infra/otel/processors/normalize-agent-fields.yaml`

Contract:

- use `otel/opentelemetry-collector-contrib`
- OTLP/HTTP receiver with `include_metadata: true`
- resource enrichment from trusted headers
- `agent.tool` normalization
- memory limiter, batch processor, sending queue, and retry-on-failure
- export to internal SigNoz OTLP/gRPC endpoint

### SigNoz

Files:

- `infra/signoz/README.md`
- `infra/signoz/dashboards/*.json`
- `compose/docker-compose.signoz.yml`

Contract:

- v1 backend for logs, traces, metrics, dashboards, and alerts
- ClickHouse-backed storage through SigNoz
- OTLP ingestion ports internal only
- retention configured deliberately

## Data Contracts

Required resource attributes:

- `telemetry.team.id`
- `telemetry.user.id`
- `telemetry.user.email`
- `telemetry.token.id`
- `telemetry.source.ip`
- `agent.tool`
- `agent.capture.profile`
- `agent.client.version`
- `agent.session.id`
- `agent.conversation.id`
- `repo.name`
- `repo.remote`
- `git.branch`
- `git.commit`
- `model.name`
- `run.mode`
- `run.outcome`

Cardinality-sensitive fields stay out of default metric group-bys:

- session id
- conversation id
- repo remote
- branch names
- command strings
- file paths
- raw API body events

## Storage And Retention

Baseline target:

- logs: 7-14 days hot
- traces: 7-14 days hot
- metrics: 30-90 days
- raw API body events: disabled by default; 1-3 days if enabled

Warehouse and S3 archive are explicitly outside v1 unless a concrete downstream
analytics or archival requirement appears.

## Milestone Boundaries

1. Local end-to-end ingestion: Compose, auth-api, Nginx, Collector, SigNoz docs,
   smoke test.
2. Codex onboarding: installer, template, docs, dashboard.
3. Claude Code onboarding: installer, default env, max-capture env, dashboard.
4. Storage guardrails: retention, queue/retry settings, ingest volume dashboard,
   optional warehouse profile.
5. Team trial operations: operating guide, troubleshooting, token lifecycle,
   dashboard import, backup/restore.

## Implementation Safety Notes

- Do not expose unauthenticated Collector or SigNoz ingestion.
- Do not trust client-supplied identity or source-IP headers.
- Do not store OTLP request bodies in auth audit records.
- Do not enable prompt, tool-content, or raw API body capture in normal
  onboarding.
- Do not add a custom OTLP parser/proxy in v1.
- Do not add SSO, public admin UI, S3 archive, or duplicate warehouse before
  the MVP contracts are satisfied.

## Known Unknowns

- No deployment environment or TLS termination layer is implemented.
- No dashboard JSON schema has been validated against SigNoz yet.
- No Collector config has been run through a Collector binary yet.
- CI validates unit, static, and Compose contracts, but does not start the full
  SigNoz stack.
