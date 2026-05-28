# AOTEL-012 Completion Note

## Summary

Implemented starter SigNoz dashboard artifacts:

- `team-usage.json`
- `codex-overview.json`
- `claude-overview.json`
- `tool-usage.json`
- `collector-health.json`

Each dashboard includes the required user, team, tool, and capture-profile
filters. Default group-bys avoid session id, conversation id, branch, command
text, file path, and full repo remote fields. The SigNoz README now documents
manual import limitations until a live SigNoz schema is validated.

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
38 passed in 0.39s
```

```sh
python -m json.tool infra/signoz/dashboards/*.json
```

Result: all dashboard JSON files parse.

```sh
git diff --check
```

Result: clean.

## Deviations

- Dashboard files are starter contracts, not finalized SigNoz UI exports. They
  need live import validation once SigNoz is running.

## Risks

- Query names and metric names may need adjustment after the first real Codex
  and Claude Code telemetry arrives.
