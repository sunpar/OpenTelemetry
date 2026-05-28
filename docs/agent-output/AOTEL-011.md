# AOTEL-011 Completion Note

## Summary

Implemented Claude Code onboarding artifacts:

- normal `templates/claude.env` with OTel metrics, logs, traces, endpoint, and
  bearer auth
- `templates/claude.max-capture.env` overlay for prompt, tool, content, and raw
  API body capture
- `scripts/install-claude-otel.sh` with `--endpoint`, `--token`, `--profile`,
  `--token-capture-profile`, and `--output`
- max profile refusal unless `--token-capture-profile max` is provided
- no shell startup file mutation
- tests for generated shell syntax, safe normal defaults, max-capture overlay,
  and startup-file preservation

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
33 passed in 0.40s
```

```sh
bash -n scripts/install-claude-otel.sh templates/claude.env templates/claude.max-capture.env
```

Result: clean.

```sh
git diff --check
```

Result: clean.

## Deviations

- `shellcheck` is not installed in this environment, so the requested shellcheck
  command could not run. `bash -n` and behavior tests ran instead.

## Risks

- The max-profile check is argument-based until auth-api/otelctl can pass
  trusted token metadata into the installer.
