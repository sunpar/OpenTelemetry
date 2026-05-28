# Agent OTel Trial Implementation Plan

Last updated: 2026-05-28

## Scope

Build the initial internal product described by the repository docs: auth-api,
authenticated OTLP ingress, Collector gateway, SigNoz bootstrap, Codex and
Claude Code onboarding, dashboards, smoke tests, and operations guardrails.

This plan is implementation-ready but does not implement source files itself.

## Source Documents

- `README.md`
- `docs/architecture.md`
- `docs/token-model.md`
- `docs/data-model.md`
- `docs/onboarding.md`
- `docs/operating.md`
- `docs/storage-retention.md`
- `docs/troubleshooting.md`
- `docs/milestones.md`
- `docs/agent-context/repo-map.md`
- `docs/agent-context/test-commands.md`
- `docs/agent-context/architecture-index.md`

## Assumptions

- V1 uses Python/FastAPI for `auth-api` and Python for `otelctl`.
- SQLite is the v1 token database.
- SigNoz is the only v1 backend.
- Normal client onboarding is content-minimal.
- Max capture is opt-in, token-scoped, and short-lived.
- Docker Compose is the local trial runtime.

## Open Questions

- Which Python packaging workflow should be used for multi-package local
  development: independent `pyproject.toml` files, a root workspace, or `uv`
  workspaces?
- Should SigNoz be cloned/pinned under `.vendor/signoz` or represented by a
  wrapper Compose file in v1?
- Which CI provider should run the eventual validation suite?
- Which production TLS boundary will host `https://otel.yourcompany.com`?

## Epics

| Epic | Summary |
| --- | --- |
| E01 Control plane | auth-api, SQLite schema, token lifecycle, `otelctl` |
| E02 Gateway path | Nginx ingress, Collector gateway, Compose stack |
| E03 Backends and dashboards | SigNoz bootstrap, dashboard JSON, retention notes |
| E04 Client onboarding | Codex and Claude Code templates/installers |
| E05 Validation and operations | smoke tests, Make targets, security checks |

## Wave Plan

| Wave | Tasks | Intent |
| ---: | --- | --- |
| 1 | AOTEL-001, AOTEL-005, AOTEL-006, AOTEL-008, AOTEL-010, AOTEL-011, AOTEL-012 | Independent scaffolding, configs, templates, and dashboards |
| 2 | AOTEL-002 | Auth database and token primitives |
| 3 | AOTEL-003, AOTEL-004 | API and CLI on top of token primitives |
| 4 | AOTEL-007 | Compose and Make integration after services/configs exist |
| 5 | AOTEL-009 | End-to-end smoke and security checks |

## Post-Wave Verification

After each wave:

```sh
git diff --check
```

After implementation introduces Python packages:

```sh
python -m pytest
python -m ruff check .
```

After Compose and Collector configs exist:

```sh
docker compose -f compose/docker-compose.gateway.yml config
docker compose -f compose/docker-compose.signoz.yml config
```

After Milestone 1:

```sh
make signoz-up
make up
make smoke TOKEN=<issued-token>
```

## Task Index

- `tasks/AOTEL-001.md`: Project scaffold and developer ergonomics
- `tasks/AOTEL-002.md`: Auth storage and token primitives
- `tasks/AOTEL-003.md`: Auth API verification endpoint
- `tasks/AOTEL-004.md`: `otelctl` user and token CLI
- `tasks/AOTEL-005.md`: Nginx authenticated OTLP ingress
- `tasks/AOTEL-006.md`: Collector gateway configuration
- `tasks/AOTEL-007.md`: Gateway Compose stack and Make targets
- `tasks/AOTEL-008.md`: SigNoz bootstrap
- `tasks/AOTEL-009.md`: Smoke and security verification scripts
- `tasks/AOTEL-010.md`: Codex onboarding generator
- `tasks/AOTEL-011.md`: Claude Code onboarding generator
- `tasks/AOTEL-012.md`: Starter SigNoz dashboards
