# Acceptance Test Coverage

Last updated: 2026-05-28

This file translates repository acceptance criteria into testable scenarios for
future implementation tasks. It is not an executable test suite yet.

## Milestone 1: Local End-To-End Ingestion

| Criterion | Test Scenario | Expected Result | Primary Task |
| --- | --- | --- | --- |
| `make up` starts auth-api, Nginx, and Collector | Run `make up`, then inspect `docker compose ps` | auth-api, nginx, and otel-collector are running | AOTEL-007 |
| `make signoz-up` starts SigNoz | Run `make signoz-up`, then inspect SigNoz containers | SigNoz UI/storage containers are running | AOTEL-008 |
| `otelctl users add` works | Add `alice@example.com` in `quant-dev` | User row exists with active status | AOTEL-004 |
| `otelctl tokens issue` works | Issue a token for the user | Token is printed once; DB stores only hash/prefix/last4 | AOTEL-004 |
| Invalid token returns 401 | POST to `/v1/logs` with `Bearer invalid` | Response status is 401 | AOTEL-003, AOTEL-009 |
| Valid token reaches Collector | Send test log through Nginx with valid token | Collector debug exporter or SigNoz receives test log | AOTEL-007, AOTEL-009 |
| All OTLP paths require auth | POST no/invalid token to logs/traces/metrics | All three paths reject unauthenticated requests | AOTEL-005, AOTEL-009 |
| Direct Collector and SigNoz OTLP ports are not host-published | Probe host ports 4317/4318 outside gateway | Direct unauthenticated ingest is unavailable | AOTEL-007, AOTEL-009 |
| Spoofed client telemetry headers are overwritten | Send valid request with fake `X-Telemetry-*` headers | SigNoz shows auth-api identity, not spoofed values | AOTEL-005, AOTEL-009 |
| SigNoz shows trusted attributes | Query test log in SigNoz | `telemetry.user.email`, `telemetry.team.id`, `telemetry.token.id`, `agent.capture.profile` exist | AOTEL-006, AOTEL-009 |

## Milestone 2: Codex Onboarding

| Criterion | Test Scenario | Expected Result | Primary Task |
| --- | --- | --- | --- |
| User runs installer with token | Run installer in temp HOME with endpoint/token | Managed Codex OTel block is written | AOTEL-010 |
| `~/.codex/config.toml` is backed up | Start with existing config | Timestamped backup exists and original settings are preserved | AOTEL-010 |
| Codex sends logs, metrics, traces | Run Codex with generated config against local gateway | Gateway receives all configured signal types | AOTEL-010, AOTEL-009 |
| SigNoz filters Codex data by user/team | Query generated Codex telemetry | User/team filters return only that user's records | AOTEL-006, AOTEL-012 |
| Prompt content appears only when enabled | Compare normal and content-capture overlay | Normal excludes prompt content; overlay includes it | AOTEL-010 |

## Milestone 3: Claude Code Onboarding

| Criterion | Test Scenario | Expected Result | Primary Task |
| --- | --- | --- | --- |
| User sources generated env file | Run installer and source env in shell | Required OTel env vars are present | AOTEL-011 |
| Claude Code sends logs, metrics, traces | Run Claude Code with generated env | Gateway receives configured signal types | AOTEL-011, AOTEL-009 |
| Tool details are visible when enabled | Use max-capture env | Tool detail fields appear in emitted telemetry | AOTEL-011 |
| Tool content is visible when enabled | Use max-capture env | Tool content appears only in max profile | AOTEL-011 |
| Raw API body capture is opt-in only | Inspect normal and max env files | Normal excludes raw body flag; max includes it | AOTEL-011 |

## Milestone 4: Storage Guardrails

| Criterion | Test Scenario | Expected Result | Primary Task |
| --- | --- | --- | --- |
| Logs and traces have deliberate retention | Inspect SigNoz bootstrap docs/settings | Retention values are explicit | AOTEL-008 |
| Metrics have deliberate retention | Inspect SigNoz bootstrap docs/settings | Metrics retention is explicit | AOTEL-008 |
| Raw API bodies disabled by default | Inspect templates and issued normal token | No raw body flags in normal profile | AOTEL-010, AOTEL-011 |
| Collector queue/failure metrics visible | Inspect dashboard JSON | Collector health dashboard includes queue/failure panels | AOTEL-012 |
| Ingest volume reviewable by team/user/tool | Inspect dashboards | Team usage dashboard includes team/user/tool filters | AOTEL-012 |

## Milestone 5: Team Trial Operations

| Criterion | Test Scenario | Expected Result | Primary Task |
| --- | --- | --- | --- |
| Teammate can be onboarded under five minutes | Run documented operator and teammate flow | Token and config snippets are generated with minimal manual steps | AOTEL-004, AOTEL-010, AOTEL-011 |
| Token revocation makes requests fail | Revoke active token, then send telemetry | Subsequent gateway request fails with 403 | AOTEL-002, AOTEL-003, AOTEL-009 |
| Operators can answer user activity questions | Query logs/traces by user/team/tool | Per-user Codex activity is discoverable | AOTEL-006, AOTEL-012 |
| Operators can rank users/tools by volume | Query dashboard | Ingest volume grouped by user/tool is visible | AOTEL-012 |
| Operators can detect backpressure | Inspect Collector health dashboard | Exporter queue/failure/memory limiter signals are visible | AOTEL-006, AOTEL-012 |

## Cross-Cutting Negative Tests

- Missing bearer token returns 401.
- Malformed bearer token returns 401.
- Unknown token id returns 401.
- Hash mismatch returns 401.
- Revoked token returns 403.
- Expired token returns 403.
- Disabled user returns 403.
- Scope mismatch returns 403.
- Non-OTLP path returns 404.
- Client-supplied identity headers do not reach SigNoz unchanged.
- Normal onboarding never enables prompt, tool content, or raw API body capture.
