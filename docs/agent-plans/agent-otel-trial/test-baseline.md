# Test Baseline

Last updated: 2026-05-28

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
- GitHub Actions CI

The local unit and contract suite currently passes with one opt-in live smoke
test skipped unless the gateway stack and a real token are provided.

## Environment Assumptions

- macOS local development environment.
- `zsh` shell.
- Python 3.11 available at `/opt/homebrew/bin/python3.11`.
- Docker and Docker Compose available for Compose config validation.
- Codex CLI available only for optional manual client verification.

## Setup Commands

```sh
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
```

## Baseline Commands

```sh
.venv/bin/python -m pytest -q
```

Expected result:

```text
94 passed, 1 skipped
```

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
make signoz-up
make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
```

The equivalent pytest smoke path is:

```sh
AOTEL_RUN_COMPOSE_SMOKE=1 AOTEL_SMOKE_TOKEN=<issued-token> \
  .venv/bin/python -m pytest tests/test_aotel009_smoke_scripts.py -q
```

## Current Failure List

No baseline unit, lint, docs, or Compose config failures are expected. The
remaining unproven areas are live SigNoz ingestion, dashboard import behavior,
Collector binary validation, and real Codex/Claude telemetry emission.
