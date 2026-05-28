# Test Commands

Last updated: 2026-05-28

## Current Test Status

The repository has runnable Python packages, Compose contracts, installer
scripts, dashboard JSON, and GitHub Actions CI.

Latest local baseline for the merged implementation:

```text
94 passed, 1 skipped
```

The skipped test is the opt-in live gateway smoke test, which requires a
running local Compose stack and a real issued token.

## Local Setup

Run from the repository root:

```sh
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` installs both local Python packages in editable mode:

- `services/auth-api`
- `cli/otelctl`

It also installs the test and validation tools used by CI.

## Package Manager Discovery

Current package, build, and runtime files:

```text
Makefile
requirements-dev.txt
cli/otelctl/pyproject.toml
compose/docker-compose.gateway.yml
compose/docker-compose.signoz.override.yml
compose/docker-compose.signoz.yml
services/auth-api/pyproject.toml
.github/workflows/ci.yml
```

## Fast Local Verification

Run the main Python test suite:

```sh
.venv/bin/python -m pytest -q
```

Run the Python linter:

```sh
.venv/bin/python -m ruff check .
```

Run repository static checks:

```sh
.venv/bin/python scripts/check-docs.py
git diff --check
```

`scripts/check-docs.py` validates:

- ASCII text and trailing whitespace for tracked text files
- internal Markdown links
- TOML snippets in `docs/onboarding.md`
- SigNoz dashboard JSON
- shell syntax for `scripts/*.sh`

## Targeted Test Commands

Auth domain and `otelctl` behavior:

```sh
.venv/bin/python -m pytest services/auth-api/tests cli/otelctl/tests -q
```

Gateway, Collector, and SigNoz config:

```sh
.venv/bin/python -m pytest \
  tests/test_aotel005_nginx.py \
  tests/test_aotel006_collector.py \
  tests/test_aotel007_gateway_compose.py \
  tests/test_aotel008_signoz.py \
  -q
```

Installers and smoke scripts:

```sh
.venv/bin/python -m pytest \
  tests/test_aotel009_smoke_scripts.py \
  tests/test_aotel010_codex_installer.py \
  tests/test_aotel011_claude_installer.py \
  -q
```

CI contract checks:

```sh
.venv/bin/python -m pytest tests/test_ci_contract.py -q
```

## Compose Verification

Validate the local gateway stack:

```sh
docker compose -f compose/docker-compose.gateway.yml config
```

Validate the lightweight SigNoz wrapper contract:

```sh
docker compose -f compose/docker-compose.signoz.yml config
```

Validate the SigNoz override against a real upstream compose file after the
pinned SigNoz checkout exists:

```sh
docker compose \
  -f .vendor/signoz/deploy/docker/docker-compose.yaml \
  -f compose/docker-compose.signoz.override.yml \
  config
```

## Useful Manual Checks

Make help and missing-variable guards:

```sh
make help
make user
```

Shell parse checks:

```sh
bash -n scripts/install-codex-otel.sh
bash -n scripts/install-claude-otel.sh
bash -n templates/claude.env
bash -n templates/claude.max-capture.env
```

## Live Milestone Verification

These checks require Docker and a running local stack:

```sh
make signoz-up
make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
curl -i http://localhost:8088/v1/logs -H 'Authorization: Bearer invalid'
curl -fsS http://localhost:8088/healthz
docker compose -f compose/docker-compose.gateway.yml ps
docker compose -f compose/docker-compose.gateway.yml logs -f auth-api
docker compose -f compose/docker-compose.gateway.yml logs -f nginx
docker compose -f compose/docker-compose.gateway.yml logs -f otel-collector
```

The live smoke test also supports:

```sh
AOTEL_RUN_COMPOSE_SMOKE=1 AOTEL_SMOKE_TOKEN=<issued-token> \
  .venv/bin/python -m pytest tests/test_aotel009_smoke_scripts.py -q
```

## Onboarding Verification

Codex installer:

```sh
bash scripts/install-codex-otel.sh --endpoint "$ENDPOINT" --token "$TOKEN"
```

Claude Code installer:

```sh
bash scripts/install-claude-otel.sh --endpoint "$ENDPOINT" --token "$TOKEN"
```

Use temporary home directories for destructive installer checks, or rely on the
pytest coverage in `tests/test_aotel010_codex_installer.py` and
`tests/test_aotel011_claude_installer.py`.

## CI Status

GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

CI currently runs:

- Python package install from `requirements-dev.txt`
- `ruff check`
- `pytest`
- docs, dashboard JSON, and shell syntax checks
- `git diff --check` against the committed PR or push range
- Docker Compose config validation for gateway and SigNoz wrapper files

CI intentionally does not start the full SigNoz stack or run live telemetry
smoke tests yet; those remain manual milestone checks until the stack startup
time and credentials are appropriate for CI.

## Remaining Verification Gaps

- Dashboard JSON has not been imported into a live SigNoz instance.
- The Collector config has not been validated with the Collector binary.
- Codex and Claude Code telemetry should still be verified against current
  installed client versions.
- Live smoke testing still depends on an operator-issued token.
