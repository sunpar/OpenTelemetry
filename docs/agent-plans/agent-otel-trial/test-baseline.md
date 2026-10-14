# Test Baseline

Last updated: 2026-10-14

## Baseline Summary

The repository has an implemented local MVP baseline for the authenticated agent
OpenTelemetry gateway:

- FastAPI auth-api package
- local `otelctl` CLI package
- Nginx ingress config
- OpenTelemetry Collector configs
- Docker Compose contracts
- SigNoz bootstrap wrapper and dashboards
- Codex and Claude Code installers
- smoke/security scripts
- manual GitHub Actions verification

The local unit and contract suite runs offline. Live gateway smoke uses `make smoke` with an operator-issued token.

## Environment Assumptions

- macOS local development environment.
- `zsh` shell.
- Python 3.11 available at `/opt/homebrew/bin/python3.11`.
- Docker and Docker Compose available for Compose config validation.
- Codex CLI available only for optional manual client verification.

## Setup Commands

```sh
make install-dev
make setup-hooks
```

## Baseline Commands

```sh
.venv/bin/python -m pytest -q
```

Expected result: all unit and contract tests pass without running live gateway smoke.

```sh
.venv/bin/python -m ruff check .
```

Expected result:

```text
All checks passed!
```

```sh
.venv/bin/python scripts/check-docs.py
git diff --check
```

Expected result: no reported failures.

```sh
docker compose -f compose/docker-compose.gateway.yml config
docker compose -f compose/docker-compose.signoz.yml config
```

Expected result: both Compose files render successfully.

## Live Checks

Run these only when Docker can start containers and a real token is available:

```sh
AOTEL_OTLP_UPSTREAM=http://127.0.0.1:4318 make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
```

## Current Failure List

No baseline unit, lint, docs, or Compose config failures are expected. The
remaining unproven areas are live SigNoz ingestion, dashboard import behavior,
Collector binary validation, and real Codex/Claude telemetry emission.
