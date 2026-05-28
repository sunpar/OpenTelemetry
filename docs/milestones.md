# Milestones

This project should ship in small, testable increments. The first useful
version is token issuance, auth proxy, Collector gateway, SigNoz bootstrap,
Codex/Claude installers, and dashboards.

## Milestone 1: Local End-To-End Ingestion

Deliverables:

- `compose/docker-compose.gateway.yml`
- `services/auth-api`
- `infra/nginx/nginx.conf`
- `infra/otel/collector.local.yaml`
- SigNoz bootstrap instructions
- smoke-test script

Acceptance criteria:

1. `make up` starts auth-api, Nginx, and Collector.
2. `make signoz-up` starts SigNoz.
3. `otelctl users add` works.
4. `otelctl tokens issue` works.
5. Invalid token returns 401.
6. Valid token reaches Collector.
7. SigNoz shows a test log with:
   - `telemetry.user.email`
   - `telemetry.team.id`
   - `telemetry.token.id`

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
4. SigNoz can filter Codex data by user and team.
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

## Milestone 4: Storage Guardrails

Deliverables:

- `docs/storage-retention.md`
- SigNoz retention recommendations
- Collector queue and retry settings
- basic ingest volume dashboard
- optional warehouse profile

Acceptance criteria:

1. Logs and traces have deliberate retention.
2. Metrics have deliberate retention.
3. Raw API bodies are disabled by default.
4. Collector queue size/capacity/failure metrics are visible.
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
3. Operators can answer "what did Alice's Codex do today?"
4. Operators can answer "which users/tools generated the most telemetry?"
5. Operators can detect Collector/exporter backpressure.

## Not In V1

- Custom OTLP parser or proxy.
- SSO.
- S3 archive.
- Full schema normalization.
- Public admin UI.
- Duplicate custom warehouse.
