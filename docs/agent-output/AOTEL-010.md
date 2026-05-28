# AOTEL-010 Completion Note

## Summary

Implemented Codex onboarding artifacts:

- parseable `templates/codex.config.toml`
- `scripts/backup-codex-config.sh` timestamped backup helper
- `scripts/install-codex-otel.sh` installer with `--endpoint`, `--token`, and
  `--profile normal|max`
- managed block replacement using explicit start/end markers
- preservation of unrelated Codex config
- normal profile defaulting `log_user_prompt=false`
- tests covering template parse, backup creation, replacement behavior, and
  shell syntax

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
27 passed in 0.31s
```

```sh
bash -n scripts/install-codex-otel.sh scripts/backup-codex-config.sh
```

Result: clean.

```sh
git diff --check
```

Result: clean.

Additional check:

```sh
CODEX_HOME=<temp> codex doctor --json
```

Result: the installed Codex CLI accepted the rendered temporary config load.

## Deviations

- `shellcheck` is not installed in this environment, so the requested shellcheck
  command could not run. `bash -n` and behavior tests ran instead.

## Risks

- The installed Codex CLI accepted config loading, but telemetry emission still
  needs an end-to-end gateway smoke test after AOTEL-007 and AOTEL-009.
