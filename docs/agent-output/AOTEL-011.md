# AOTEL-011 Completion Note

## Summary

Implemented Claude Code onboarding artifacts:

- normal `templates/claude.env` with OTel metrics, logs, traces, endpoint, and
  bearer auth
- `templates/claude.max-capture.env` overlay for prompt, tool, content, and raw
  API body capture
- `scripts/install-claude-otel.sh` with `--endpoint`, `--token`, `--profile`,
  and `--output`
- max profile refusal until trusted token metadata is available
- shell-quoted endpoint and bearer header rendering for opaque secrets
- normal profile clears high-capture variables inherited from the parent shell
- `make install-claude ENDPOINT=... TOKEN=...` invokes the installer
- no shell startup file mutation
- tests for generated shell syntax, safe normal defaults, max-profile refusal,
  secret rendering, `--token=<secret>`, Make wiring, and startup-file preservation

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-011-claude-onboarding`:

```sh
PATH="/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
35 passed in 0.66s
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

- The installer refuses max capture until auth-api/otelctl can pass trusted
  token metadata into the installer.
