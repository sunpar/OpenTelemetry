# Targeted Review - 2026-05-28

Worktree:
`/Users/sunpar/.config/superpowers/worktrees/OpenTelemetry/codex-targeted-review-refactor-20260528`

Branch: `codex/targeted-review-refactor-20260528`

## Baseline

Setup:

```sh
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e packages/auth-core -e services/auth-api -e cli/otelctl pytest pyyaml httpx
```

Pre-refactor baseline:

```sh
.venv/bin/python -m pytest -q
```

Result: 90 passed, 1 skipped, 1 warning.

Targeted post-slice check:

```sh
.venv/bin/python -m pytest cli/otelctl/tests/test_otelctl.py services/auth-api/tests/test_tokens.py -q
```

Result: 21 passed.

Full post-slice baseline:

```sh
.venv/bin/python -m pytest -q
```

Result: 93 passed, 1 skipped, 1 warning.

Slice 2 setup refresh:

```sh
.venv/bin/python -m pip install -e packages/auth-core -e services/auth-api -e cli/otelctl
```

Slice 2 focused check:

```sh
.venv/bin/python -m pytest packages/auth-core services/auth-api/tests cli/otelctl/tests tests/test_aotel001_scaffold.py tests/test_aotel007_gateway_compose.py -q
```

Result: 45 passed.

Slice 2 full verification:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python scripts/check-docs.py
git diff --check
docker compose -f compose/docker-compose.gateway.yml config
docker compose -f compose/docker-compose.signoz.yml config
```

Result: 97 passed, 1 skipped; Ruff passed; docs/static checks passed; diff
check passed; both Compose configs validated.

## App Map

- `packages/auth-core/`: shared auth models, SQLite migration, database helpers,
  and token lifecycle logic.
- `services/auth-api/`: FastAPI token verification service, compatibility
  wrappers around auth-core, and service tests.
- `cli/otelctl/`: operator CLI, packaged templates, compatibility wrappers
  around auth-core, and CLI tests.
- `infra/nginx/`: authenticated OTLP ingress.
- `infra/otel/`: Collector local/prod profiles and normalization processor.
- `infra/signoz/`: SigNoz wrapper docs and dashboards.
- `scripts/`: installers, smoke runner, and OTLP JSON sender.
- `templates/`: Codex and Claude Code telemetry templates.
- `tests/`: cross-component scaffold, config, installer, script, and dashboard
  tests.

## Review Findings

1. Auth-domain duplication has already drifted.

   Evidence: `services/auth-api/src/tokens.py` and
   `cli/otelctl/src/otelctl_auth/tokens.py` both implement token parsing,
   issuing, validation, audit writes, scope checks, and result mapping. Before
   this slice, auth-api normalized original URIs before scope/audit checks,
   attributed malformed secrets when a visible token id was present, and rejected
   comma-delimited/unknown scopes. The CLI copy did not. The models are
   identical, migrations are identical, and database helpers differ only in
   import path, migration path, and `lastrowid` versus `RETURNING id`.

   Refactor direction: extract a single shared auth-domain package for models,
   migrations, database helpers, token logic, and tests. Keep service and CLI
   wrappers thin.

2. Generated repo context is stale.

   Evidence: `docs/agent-context/repo-map.md`,
   `docs/agent-context/test-commands.md`, and
   `docs/agentic-system/feature-model.json` still described the repo as
   documentation-only even though the app now has runnable source, Compose
   files, templates, scripts, dashboards, and tests.

   Refactor direction: keep `docs/agent-context/` current with the runnable app
   and refresh `docs/agentic-system/feature-model.json` before generating slices
   from it.

3. Auth-api packaging was still script-shaped.

   Evidence: the auth-api Dockerfile sets `PYTHONPATH=/app/src` and runs
   `uvicorn app:app`; tests import `app`, `db`, and `tokens` as top-level
   modules. The package has an `auth_api` stub, but the service code is not
   inside that package yet.

   Refactor direction: after shared auth-domain extraction, move service code
   into `auth_api.*` with compatibility wrappers or coordinated Docker/test
   updates.

4. Root setup and CI contract are implicit.

   Evidence: there is no root `pyproject.toml`, requirements file, or CI
   workflow. The working local setup is a venv with editable installs for the
   service and CLI plus `pytest`, `pyyaml`, and `httpx`.

   Refactor direction: add a root test target or CI workflow once the package
   boundaries are stable.

## First Slice Applied

Scope: bring `otelctl_auth.tokens` into semantic parity with auth-api token
validation without changing the service path.

Changes:

- Added CLI-side original URI normalization before scope checks and audit rows.
- Added visible-token-id auditing for malformed token secrets.
- Added CLI-side scope validation for comma-delimited and unsupported scopes.
- Added regression tests in `cli/otelctl/tests/test_otelctl.py`.

Files changed:

- `cli/otelctl/src/otelctl_auth/tokens.py`
- `cli/otelctl/tests/test_otelctl.py`
- `docs/agent-context/repo-map.md`
- `docs/agent-context/test-commands.md`
- `docs/agentic-system/targeted-review-2026-05-28.md`

## Second Slice Applied

Scope: extract the duplicated auth-domain implementation into a shared local
package while preserving existing service and CLI import surfaces.

Changes:

- Added `packages/auth-core` with the shared dataclasses, SQLite migration,
  database helpers, and token lifecycle logic.
- Replaced `services/auth-api/src/{db,models,tokens}.py` and
  `cli/otelctl/src/otelctl_auth/{db,models,tokens}.py` with compatibility
  wrappers that re-export auth-core.
- Removed the duplicated migration files from the service and CLI package.
- Updated package metadata, dev requirements, Docker build context, Compose
  build config, and package/runtime tests for the new package boundary.

Files changed:

- `packages/auth-core/`
- `requirements-dev.txt`
- `services/auth-api/pyproject.toml`
- `services/auth-api/Dockerfile`
- `services/auth-api/src/db.py`
- `services/auth-api/src/models.py`
- `services/auth-api/src/tokens.py`
- `cli/otelctl/pyproject.toml`
- `cli/otelctl/src/otelctl_auth/db.py`
- `cli/otelctl/src/otelctl_auth/models.py`
- `cli/otelctl/src/otelctl_auth/tokens.py`
- `compose/docker-compose.gateway.yml`
- `tests/test_aotel001_scaffold.py`
- `tests/test_aotel007_gateway_compose.py`
- `services/auth-api/tests/test_runtime_config.py`
- `tests/test_ci_contract.py`
- repo context docs

## Next Slices

## Third Slice Applied

Scope: move the auth-api runtime entrypoint and settings into the `auth_api`
package while preserving old import paths as compatibility wrappers.

Changes:

- Added `auth_api.app` and `auth_api.settings` as the packaged runtime modules.
- Reduced top-level `app.py` and `settings.py` to compatibility wrappers.
- Updated Docker to run `uvicorn auth_api.app:app`.
- Updated auth-api tests and package metadata tests to use the package modules.
- Refreshed README and agent-context docs for the package shape.

Focused check:

```sh
.venv/bin/python -m pytest services/auth-api/tests tests/test_aotel001_scaffold.py -q
```

Result: 27 passed.

Files changed:

- `services/auth-api/src/auth_api/app.py`
- `services/auth-api/src/auth_api/settings.py`
- `services/auth-api/src/app.py`
- `services/auth-api/src/settings.py`
- `services/auth-api/Dockerfile`
- `services/auth-api/tests/test_auth_api.py`
- `services/auth-api/tests/test_runtime_config.py`
- `tests/test_aotel001_scaffold.py`
- repo context docs

## Next Slices

## Fourth Slice Applied

Scope: refresh `docs/agentic-system/feature-model.json` so planning data
matches the implemented and stacked app shape.

Changes:

- Added the shared auth-core component to the architecture model.
- Updated token-control-plane code paths for `packages/auth-core` and packaged
  `auth_api` modules.
- Removed stale doc/code mismatch notes for SigNoz, installers, and operations.
- Updated tests, entry points, unknowns, and evidence for CI, dashboards,
  installers, and package boundaries.

Focused check:

```sh
.venv/bin/python -m json.tool docs/agentic-system/feature-model.json
```

Result: feature model JSON parses successfully.

Files changed:

- `docs/agentic-system/feature-model.json`
- `docs/agentic-system/targeted-review-2026-05-28.md`

## Next Slices

## Fifth Slice Applied

Scope: expose the repo's local verification contract as root Make targets.

Changes:

- Added `install-dev`, `lint`, `test`, `static-check`, `compose-config`, and
  `check` targets.
- Added configurable `PYTHON` and `DOCKER_COMPOSE` variables.
- Updated existing Compose-backed targets to use `DOCKER_COMPOSE`.
- Added tests that assert the root validation contract is wired.
- Updated agent-context docs with the Make-based verification path.

Review follow-up:

- `static-check` now validates both unstaged and staged whitespace changes.
- `compose-config` now validates the same SigNoz upstream compose plus safe
  override path used by `make signoz-up`; CI runs the same override check.

Verification:

```sh
make check PYTHON=.venv/bin/python
.venv/bin/python -m pytest tests/test_aotel001_scaffold.py tests/test_aotel007_gateway_compose.py tests/test_ci_contract.py -q
.venv/bin/python scripts/check-docs.py
git diff --check
```

Result: `make check` passed with 98 passed, 1 skipped; focused contract tests
passed with 18 passed; static checks and diff check passed.

Files changed:

- `Makefile`
- `tests/test_aotel001_scaffold.py`
- `tests/test_aotel007_gateway_compose.py`
- `tests/test_ci_contract.py`
- `docs/agent-context/repo-map.md`
- `docs/agent-context/test-commands.md`
- `docs/agentic-system/targeted-review-2026-05-28.md`

## Next Slices

- No additional review/refactor slices are currently queued in this artifact.
  New slices should come from CI failures, PR review feedback, or a refreshed
  feature/slice plan after the stacked PRs merge.
