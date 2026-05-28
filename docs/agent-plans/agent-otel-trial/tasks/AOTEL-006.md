# AOTEL-006: Collector Gateway Configuration

## Objective

Add local and production Collector gateway configs with metadata enrichment,
agent normalization, batching, queues, retry, and SigNoz export.

## Context To Load

- `docs/architecture.md`
- `docs/data-model.md`
- `docs/storage-retention.md`

## Read Set

- `docs/architecture.md`
- `docs/data-model.md`

## Write Set

- `infra/otel/collector.local.yaml`
- `infra/otel/collector.prod.yaml`
- `infra/otel/processors/normalize-agent-fields.yaml`

## Dependencies

None.

## Non-Goals

- Do not add custom OTLP parsing.
- Do not add a secondary warehouse exporter.

## Implementation Steps

1. Configure OTLP/HTTP receiver with `include_metadata: true`.
2. Map trusted metadata headers to resource attributes.
3. Normalize `agent.tool` for Codex and Claude Code.
4. Configure memory limiter, batch processor, sending queue, retry, and debug
   exporter.
5. Keep SigNoz export internal.

## Tests To Write First

- YAML parse test.
- Config assertion for `include_metadata` and trusted attributes.
- Config assertion for sending queue and retry.

## Verification Commands

```sh
git diff --check
```

## Acceptance Criteria

- Collector config includes all required `telemetry.*` attributes.
- `agent.capture.profile` is copied from trusted metadata.
- Exporter queue and retry are enabled.

## Review Focus

- Header metadata names.
- Pipeline coverage for logs, traces, and metrics.
- Resilience defaults.

## Rollback Notes

Remove `infra/otel` files.
