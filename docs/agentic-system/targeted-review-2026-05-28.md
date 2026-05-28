# Targeted Review - 2026-05-28

Worktree:
`/Users/sunpar/.config/superpowers/worktrees/OpenTelemetry/codex-targeted-review-refactor-20260528`

Branch: `codex/targeted-review-refactor-20260528`

## Baseline

Setup:

```sh
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e services/auth-api -e cli/otelctl pytest pyyaml httpx
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

## App Map

- `services/auth-api/`: FastAPI token verification service, SQLite migrations,
  auth-domain helpers, and service tests.
- `cli/otelctl/`: operator CLI, packaged templates, duplicated auth-domain
  helpers, and CLI tests.
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

3. Auth-api packaging is still script-shaped.

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

## Next Slices

1. Extract shared auth core.

   Create one importable package for `User`, `TokenRecord`, `ValidationResult`,
   SQLite migrations, database helpers, and token lifecycle logic. Then update
   auth-api and `otelctl` to import that package. This removes the highest-risk
   duplication.

2. Package auth-api under `auth_api`.

   Move service modules into the package namespace and update Docker/test entry
   points from `app:app` to `auth_api.app:app` once shared auth core exists.

3. Refresh feature model.

   Update `docs/agentic-system/feature-model.json` so component status, code
   paths, test commands, and doc/code mismatch notes match the current app.

4. Add root verification contract.

   Add one root-level test target and initial CI job for Python tests, shell
   parse checks, Compose config validation, and `git diff --check`.
