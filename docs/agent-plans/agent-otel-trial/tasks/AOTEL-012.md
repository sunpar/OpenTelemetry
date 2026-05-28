# AOTEL-012: Starter SigNoz Dashboards

## Objective

Add initial SigNoz dashboard JSON stubs and import docs for team usage, Codex,
Claude, tool usage, and Collector health.

## Context To Load

- `docs/data-model.md`
- `docs/storage-retention.md`
- `docs/operating.md`

## Read Set

- `docs/data-model.md`
- `docs/storage-retention.md`

## Write Set

- `infra/signoz/dashboards/codex-overview.json`
- `infra/signoz/dashboards/claude-overview.json`
- `infra/signoz/dashboards/team-usage.json`
- `infra/signoz/dashboards/collector-health.json`
- `infra/signoz/dashboards/tool-usage.json`

## Dependencies

None.

## Non-Goals

- Do not optimize queries before live data exists.
- Do not group metrics by high-cardinality fields by default.

## Implementation Steps

1. Create dashboard JSON files for documented starter set.
2. Use team, user, tool, model, and capture filters.
3. Avoid session id, branch, command text, and file paths as default metric
   group-bys.
4. Document manual import limitations if SigNoz schema is not finalized.

## Tests To Write First

- JSON syntax validation.
- Static scan for prohibited high-cardinality default group-bys.

## Verification Commands

```sh
json validation
git diff --check
```

## Acceptance Criteria

- Dashboard files exist for Codex, Claude, team usage, tool usage, and Collector
  health.
- Dashboards include `telemetry.user.email`, `telemetry.team.id`, `agent.tool`,
  and `agent.capture.profile` filters.
- Collector health dashboard includes exporter queue/failure indicators.

## Review Focus

- Cardinality safety.
- Importability.
- Alignment with data model docs.

## Rollback Notes

Remove dashboard JSON files.
