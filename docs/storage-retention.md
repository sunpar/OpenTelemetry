# Storage and Retention

The v1 storage strategy is one backend: SigNoz. Do not duplicate all telemetry
into a custom warehouse until there is a concrete SQL or archival requirement
that SigNoz cannot satisfy.

## Baseline Retention

Recommended starting point:

| Signal | Retention |
| --- | --- |
| Logs | 7-14 days hot |
| Traces | 7-14 days hot |
| Metrics | 30-90 days |
| Raw API body events | disabled by default; 1-3 days if enabled |

SigNoz self-hosted docs currently describe default retention as 15 days for
logs/traces and 30 days for metrics. For this trial, choose the retention value
based on volume and whether max-capture data is enabled.

## Guardrails

- Raw API body capture is off by default.
- Max capture is short-window and explicitly opted into.
- Dashboards do not group by session id, prompt id, full command text, file
  path, or full repo path by default.
- Collector exporters use sending queues and retries.
- The Collector health dashboard tracks queue size, queue capacity, exporter
  failures, refused telemetry, and memory limiter activity.
- Review SigNoz disk growth during the first week of team usage.

## Optional Warehouse Profile

Do not build this first. Add it when the team needs custom SQL outside SigNoz or
a downstream analytics contract.

Future shape:

```text
Collector
  -> SigNoz for UI and dashboards
  -> ClickHouse exporter for custom SQL tables
```

If a ClickHouse exporter is added, keep the batch processor in front of it.
ClickHouse performs better with batched inserts, and the Collector remains the
receive/process/export layer.

## S3 Archive

Avoid S3 archive in v1. It adds storage, lifecycle, format, and retrieval
decisions before the pilot has proven what needs long-term retention.

If archive becomes necessary, define:

- signal coverage
- encoding format
- partition strategy
- retention class
- replay path
- access controls
- expected query pattern

## Source Notes

- SigNoz retention period docs: https://signoz.io/docs/userguide/retention-period/
- OpenTelemetry ClickHouse exporter: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/clickhouseexporter
- ClickHouse observability guide: https://clickhouse.com/docs/observability
- OpenTelemetry Collector AWS S3 exporter: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/awss3exporter
