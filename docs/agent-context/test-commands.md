# Test Commands

Last updated: 2026-10-14

## Current Test Status

`make check` runs the native gateway's Python tests, lint, and docs checks locally. Tests block external socket connections and use temporary SQLite databases and loopback HTTP services. Live gateway verification uses the explicit `make smoke` command with a running gateway and an issued token.

## Local Setup

Run from the repository root:

```sh
make install-dev
make setup-hooks
```

`requirements-dev.txt` installs all local Python packages in editable mode:

- `packages/auth-core`
- `services/auth-api`
- `cli/otelctl`

Setup requires Python 3.11 and uv. It recreates `.venv` from `requirements-dev.lock` and installs the local packages. After changing dependency manifests, run `make lock`, then `make install-dev`, and stage the lock with the manifests. Setup may download dependencies; Git gates use the local cache offline and fail if a required wheel is missing.

## Package Manager Discovery

Current package, build, and runtime files:

```text
Makefile
requirements-dev.txt
requirements-dev.lock
pytest.ini
.githooks/pre-commit
.githooks/pre-push
scripts/git-gate.py
packages/auth-core/pyproject.toml
cli/otelctl/pyproject.toml
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
git diff --cached --check
```

`scripts/check-docs.py` validates:

- ASCII text and trailing whitespace for tracked text files
- internal Markdown links
- TOML snippets in `docs/onboarding.md`
- SigNoz dashboard JSON
- shell syntax for `scripts/*.sh`

Validate legacy Compose contracts only when reviewing old Docker reference
files:

```sh
make legacy-compose-config
```

`make legacy-compose-config` validates the gateway compose file, the SigNoz
wrapper, and the SigNoz upstream compose plus safe override path. It is not part
of the default runtime or `make check`. Docker tests use the `legacy_compose` marker, which ordinary pytest excludes; this explicit target selects them and checks safe port bindings and the missing-vendor fallback.

## Targeted Test Commands

Root Make verification contract:

```sh
make install-dev
make lint
make test
make static-check
make check
make smoke-check
make verify
make coverage
```

`make verify` runs the full checks against HEAD in an isolated archive with pinned dependencies. Use `REF=commit` to check another committed snapshot. Precommit checks the exact staged tree with `make smoke-check`. Prepush verifies outgoing commits for branches with open PRs and for `main`; failed PR lookup stops the push. Neither gate needs Docker or starts a runtime.

Create a PR through the supported wrapper:

```sh
make pr ARGS='--title "Update gateway config" --body-file /tmp/pr-body.txt'
```

The wrapper verifies HEAD, pushes that exact commit to origin, and creates a self-assigned PR. For a fork, it targets the parent repository with the fork owner's branch as the head. It accepts metadata options and rejects head/repository overrides. Git has no PR creation hook: website/API creation, direct `gh pr create`, and bypassed hooks can skip the gate. Each checkout must enable hooks with `make setup-hooks`.

Auth domain and `otelctl` behavior:

```sh
.venv/bin/python -m pytest services/auth-api/tests cli/otelctl/tests -q
```

Native gateway behavior:

```sh
.venv/bin/python -m pytest services/auth-api/tests/test_native_gateway.py -q
```

Legacy gateway, Collector, and SigNoz config:

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

These checks are for legacy reference files only and require Docker:

```sh
docker compose -f compose/docker-compose.signoz.yml config
docker compose -f compose/docker-compose.gateway.yml config
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

These checks require a running native FastAPI gateway and a real issued token:

```sh
AOTEL_OTLP_UPSTREAM=http://127.0.0.1:4318 make native-up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
curl -i http://localhost:8088/v1/logs -H 'Authorization: Bearer invalid'
curl -fsS http://localhost:8088/healthz
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

GitHub Actions runs only through `workflow_dispatch`, with full, smoke, and coverage choices. All choices use the same pinned dependencies and snapshot verification commands as local gates. Full and coverage runs also validate the legacy Compose files on Ubuntu; coverage uploads `coverage.xml`. The job has a ten-minute limit.

At migration time, `main` had no branch protection or ruleset-required statuses, so no protection change was needed. Routine pushes and PRs no longer launch hosted verification. There are no deployment or release workflows in this repository. Live SigNoz ingestion and Collector binary validation remain separate manual checks.

## Remaining Verification Gaps

- Dashboard JSON has not been imported into a live SigNoz instance.
- The Collector config has not been validated with the Collector binary.
- Codex and Claude Code telemetry should still be verified against current
  installed client versions.
- Live smoke testing still depends on an operator-issued token.
