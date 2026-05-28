# AOTEL-004 Completion

## Changes

- Added the `otelctl` operator CLI for local user and token administration.
- Implemented `users add`, `users disable`, `tokens issue`, `tokens list`, and `tokens revoke`.
- Added expiry duration parsing for `m`, `h`, and `d` units.
- Rendered Codex and Claude Code onboarding snippets during token issuance while printing the raw token only once.
- Added CLI packaging metadata for the `otelctl` entry point.

## Verification

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest cli/otelctl/tests -q
# 4 passed in 0.04s

PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
# 56 passed, 1 warning in 0.62s

git diff --check
# no output
```

The warning is the existing Starlette/FastAPI TestClient deprecation warning from the test environment.

## Risks And Deviations

- The task write set did not list `cli/otelctl/pyproject.toml`, but the entry point metadata is required for the CLI command to install cleanly.
- `otelctl` imports the auth storage modules from this monorepo layout. The gateway compose task should run it from the repository image or auth service context rather than treating it as a standalone published package yet.
