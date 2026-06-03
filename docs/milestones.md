# Milestones

Ship in small, testable increments. The MVP is token issuance, a native FastAPI
OTLP gateway, upstream forwarding, Codex/Claude installers, and dashboards.

## Milestone 1: Local End-To-End Ingestion

Deliverables:

- `services/auth-api`
- `services/auth-api/src/auth_api/gateway.py`
- native or external OTLP upstream configuration
- smoke-test script

Acceptance criteria:

1. `AOTEL_OTLP_UPSTREAM=... make native-up` starts the FastAPI auth/gateway.
2. The repository runtime does not require Docker images.
3. `otelctl users add` works.
4. `otelctl tokens issue` works.
5. Invalid token returns 401.
6. Valid token reaches the configured OTLP upstream.
7. All three OTLP paths require auth:
   - `/v1/logs`
   - `/v1/traces`
   - `/v1/metrics`
8. Spoofed client `X-Telemetry-*` headers are overwritten by the gateway.
9. A smoke test sends a spoofed forwarding header so the backend can verify
   `telemetry.source.ip` is gateway-derived, not the spoofed client value.
10. The configured backend shows a test log, span, and metric from `/v1/logs`,
   `/v1/traces`, and `/v1/metrics`, each with:
   - `telemetry.user.email`
   - `telemetry.team.id`
   - `telemetry.token.id`
   - `agent.capture.profile`

## Milestone 2: Codex Onboarding

Deliverables:

- `scripts/install-codex-otel.sh`
- `templates/codex.config.toml`
- `docs/onboarding.md`
- Codex dashboard

Acceptance criteria:

1. User runs installer with token.
2. `~/.codex/config.toml` is backed up.
3. Codex sends logs, metrics, and traces to the gateway.
4. The configured backend can filter Codex data by user and team.
5. Prompt content appears when prompt logging is enabled.

## Milestone 3: Claude Code Onboarding

Deliverables:

- `scripts/install-claude-otel.sh`
- `templates/claude.env`
- `templates/claude.max-capture.env`
- Claude dashboard

Acceptance criteria:

1. User sources generated env file.
2. Claude Code sends logs, metrics, and traces.
3. Tool details are visible when enabled.
4. Tool content is visible when enabled.
5. Raw API body capture is opt-in only.
6. Max-capture env generation refuses tokens whose trusted
   `capture_profile` is not `max`.

## Milestone 4: Storage Guardrails

Deliverables:

- `docs/storage-retention.md`
- backend retention recommendations
- upstream queue and retry settings
- basic ingest volume dashboard
- optional warehouse profile

Acceptance criteria:

1. Logs and traces have deliberate retention.
2. Metrics have deliberate retention.
3. Raw API bodies are disabled by default.
4. Upstream queue size/capacity/failure metrics are visible when the upstream
   exposes them.
5. Ingest volume can be reviewed by team, user, and tool.

## Milestone 5: Team Trial Operations

Deliverables:

- `docs/operating.md`
- `docs/troubleshooting.md`
- token rotation and revocation docs
- dashboard import docs
- backup and restore notes

Acceptance criteria:

1. A teammate can be onboarded in under five minutes.
2. A token can be revoked and subsequent requests fail.
3. Operators can answer "what did this user's Codex do today?"
4. Operators can answer "which users/tools generated the most telemetry?"
5. Operators can detect upstream/exporter backpressure.

## Not In V1

- Custom OTLP parser.
- SSO.
- S3 archive.
- Full schema normalization.
- Public admin UI.
- Duplicate custom warehouse.
