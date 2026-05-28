# AOTEL-008 Completion Note

## Summary

Implemented the SigNoz bootstrap contract:

- added `compose/docker-compose.signoz.yml` as a repo-owned wrapper/contract file
- documented the official SigNoz Docker Compose startup path under `.vendor`
- documented local UI access at `http://localhost:8080`
- documented private ingestion expectations for SigNoz OTLP ports
- documented retention checks and shutdown flow

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
docker compose -f compose/docker-compose.signoz.yml config
```

Result: config rendered successfully.

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
22 passed in 0.13s
```

```sh
git diff --check
```

Result: clean.

## Deviations

- This slice does not vendor the upstream SigNoz stack. It documents the clone
  path and keeps this repo's Compose file as a lightweight network/private
  ingestion contract. That matches the "avoid vendor sprawl" review focus.

## Risks

- `make signoz-up` still needs AOTEL-007 to wire the startup command.
- If the upstream SigNoz Compose file changes paths or exposed ports, the
  wrapper docs should be refreshed before onboarding teammates.
