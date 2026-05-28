# AOTEL-001: Project Scaffold And Developer Ergonomics

## Objective

Create the minimal repository scaffold for Python services, CLI packages, local
environment defaults, ignored generated files, and root developer targets.

## Context To Load

- `README.md`
- `docs/agent-context/repo-map.md`
- `docs/agent-context/test-commands.md`
- `docs/milestones.md`

## Read Set

- `README.md`
- `docs/agent-context/repo-map.md`
- `docs/agent-context/test-commands.md`

## Write Set

- `Makefile`
- `.env.example`
- `.gitignore`
- `services/auth-api/pyproject.toml`
- `services/auth-api/src/__init__.py`
- `cli/otelctl/pyproject.toml`
- `cli/otelctl/src/__init__.py`

## Dependencies

None.

## Non-Goals

- Do not implement auth logic.
- Do not start Compose services.
- Do not add CI.

## Implementation Steps

1. Add root targets matching documented commands with clear messages where
   downstream files are not implemented yet.
2. Add non-secret `.env.example` defaults.
3. Add Python package metadata for `auth-api` and `otelctl`.
4. Add ignores for local DBs, env files, Python caches, SigNoz data, and vendor
   output.

## Tests To Write First

- Basic import/package tests once package files exist.

## Verification Commands

```sh
git diff --check
python -m pytest
```

## Acceptance Criteria

- Root Makefile contains documented targets.
- `.env.example` contains no secrets.
- Python package metadata exists for auth-api and otelctl.
- Local generated artifacts are ignored.

## Review Focus

- No secrets or user-local paths.
- Make targets do not claim working behavior before dependent tasks land.

## Rollback Notes

Remove scaffold files. No data migration required.
