# Wave Validation

Last updated: 2026-05-28

Input: `docs/agent-plans/agent-otel-trial/plan.json`

## Result

Pass.

## Dependency Graph

```text
AOTEL-001 -> AOTEL-002 -> AOTEL-003 -> AOTEL-007 -> AOTEL-009
                      \-> AOTEL-004 -/
AOTEL-005 --------------------------/
AOTEL-006 --------------------------/
AOTEL-008 --------------------------/
AOTEL-010 -------------------------------------> AOTEL-009
AOTEL-011 -------------------------------------> AOTEL-009
AOTEL-012 -------------------------------------> AOTEL-009
```

## Wave Schedule

| Wave | Tasks | Validation |
| ---: | --- | --- |
| 1 | AOTEL-001, AOTEL-005, AOTEL-006, AOTEL-008, AOTEL-010, AOTEL-011, AOTEL-012 | No dependency edges within wave. Exact file write sets are disjoint. |
| 2 | AOTEL-002 | Depends on AOTEL-001. Single-task wave. |
| 3 | AOTEL-003, AOTEL-004 | Both depend on AOTEL-002. API and CLI write sets are disjoint. |
| 4 | AOTEL-007 | Depends on scaffold, auth API/CLI, ingress, Collector, and SigNoz bootstrap. Single-task integration wave. |
| 5 | AOTEL-009 | Depends on Compose, onboarding, and dashboard artifacts. Single-task verification wave. |

## Same-Wave Write Set Safety

Wave 1 shared parent directories are creation-only and use disjoint files:

- `AOTEL-005`: `infra/nginx/*`
- `AOTEL-006`: `infra/otel/*`
- `AOTEL-008`: `compose/docker-compose.signoz.yml`, `infra/signoz/README.md`
- `AOTEL-010`: `templates/codex.config.toml`, Codex installer scripts
- `AOTEL-011`: `templates/claude*.env`, Claude installer script
- `AOTEL-012`: `infra/signoz/dashboards/*.json`

Wave 3 writes disjoint API and CLI files.

## Cycles

No dependency cycles detected.

## Risks To Recheck Before Dispatch

- If AOTEL-001 chooses a root workspace that changes CLI/auth package write
  sets, re-run this wave validation before parallel dispatch.
- If AOTEL-008 vendors SigNoz files under `.vendor/`, confirm the path is
  ignored or intentionally versioned.
- If AOTEL-012 requires edits to `infra/signoz/README.md`, it conflicts with
  AOTEL-008 and must move to a later wave or explicitly coordinate.
