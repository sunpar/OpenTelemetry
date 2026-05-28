# SigNoz Bootstrap

Use the official SigNoz Docker Compose stack for the local backend and keep this
repository focused on the gateway, auth, onboarding, and dashboard artifacts.

The repo-owned `compose/docker-compose.signoz.yml` file is a small wrapper
contract. It validates the shared network name and confirms this repo does not
publish SigNoz OTLP ingestion ports itself.

## Local Startup

Clone the upstream SigNoz deploy files under the ignored vendor directory:

```sh
git clone https://github.com/SigNoz/signoz.git .vendor/signoz
git -C .vendor/signoz checkout a8f5bdf2562c35c2896a5a287552e124fa2c0037
```

Start the official Docker stack with this repo's safety override:

```sh
docker compose \
  -f .vendor/signoz/deploy/docker/docker-compose.yaml \
  -f compose/docker-compose.signoz.override.yml \
  up -d --remove-orphans
```

Check this repo's wrapper contract:

```sh
docker compose -f compose/docker-compose.signoz.yml config
```

After AOTEL-007 wires the Makefile, `make signoz-up` should run the same
startup path or call an equivalent pinned to the same upstream revision and
override file.

## UI Access

For a local trial, open:

```text
http://localhost:8080
```

Keep UI access limited to localhost or an authenticated internal network.

## First Org Setup

SigNoz creates the first organization and first admin through the UI. For the
local trial, keep this manual; do not script or commit the admin email,
password, or session cookies.

1. Start SigNoz with `make signoz-up`.
2. Open `http://localhost:8080`.
3. Complete the first admin setup in the browser.
4. Use `Agent Telemetry Trial` as the default organization name.
5. After login, import the dashboard JSON described below.

## OpAMP Status

Keep OpAMP out of the local SigNoz collector path for now. Run the collector
from the static config managed by this repo and the pinned upstream Compose
files. The safety override removes the upstream `--manager-config` and
`--copy-path` arguments and starts the collector with:

```text
/signoz-otel-collector --config=/etc/otel-collector-config.yaml
```

This avoids the bootstrap failure mode where the manager path logs
`cannot create agent without orgId` before the first SigNoz org exists. Revisit
OpAMP when edge collectors need remote management. Until then, manage collector
config through repo-owned Compose and Collector config updates.

## Private Ingestion

Do not expose SigNoz OTLP ports to teammates. External telemetry must enter
through the authenticated gateway:

```text
client -> Nginx auth ingress -> Collector gateway -> SigNoz
```

The official SigNoz Docker stack may publish `4317` and `4318` for standalone
use. This repo's `compose/docker-compose.signoz.override.yml` removes those host
port bindings so the gateway Collector is the only supported ingestion path. The
gateway Collector should reach SigNoz over the fixed `signoz-net` Docker network
using `signoz-otel-collector:4317`.

## Retention Checks

Review retention in the SigNoz UI before onboarding teammates. Use the baseline
policy in `docs/storage-retention.md`:

- logs and traces: short hot retention for the trial
- metrics: longer retention than logs/traces
- raw API body events: disabled by default

Check disk growth during the first week and shorten retention before enabling
any max-capture profile.

## Dashboard Import

Dashboard JSON files live in:

```text
infra/signoz/dashboards/
```

`agent-telemetry-collected-data.signoz.json` is the importable SigNoz dashboard
for the local central collector. It uses the SigNoz UI dashboard schema, not the
repo-local starter contract schema. Use manual import after the first admin and
`Agent Telemetry Trial` organization exist:

1. Open SigNoz at `http://localhost:8080`.
2. Go to Dashboards.
3. Choose Import JSON.
4. Upload or paste `infra/signoz/dashboards/agent-telemetry-collected-data.signoz.json`.
5. Confirm the dashboard title is `Agent Telemetry - Collected Data`.
6. Run the smoke flow and verify the dashboard shows logs, spans, metrics,
   smoke-test visibility, and ingest-health panels.

The remaining files are repo-local starter contracts rather than SigNoz UI
exports:

- `team-usage.json`
- `codex-overview.json`
- `claude-overview.json`
- `tool-usage.json`
- `collector-health.json`

Keep the user, team, tool, service, and capture-profile filters on tenant
telemetry dashboards. Avoid default metric group-bys on session ids, branch
names, command text, file paths, or full repo remotes.

The importable dashboard's ingest-health panel is service-scoped because
Collector and gateway health logs may not carry user, team, tool, or
capture-profile attributes.

`collector-health.json` has a separate scope. It targets Collector self-metrics
such as `otelcol_exporter_send_failed_log_records`,
`otelcol_exporter_send_failed_spans`, and
`otelcol_exporter_send_failed_metric_points` after those metrics are ingested
into SigNoz. The current gateway Collector configs receive client OTLP
telemetry and export it to SigNoz; they do not scrape the gateway Collector's
own metrics endpoint. If the deployment uses this dashboard, first route
Collector self-metrics into SigNoz, then keep the dashboard filters limited to
Collector labels such as `exporter`, `receiver`, and `processor`. Do not apply
tenant-only filters such as `telemetry.user.email`, `telemetry.team.id`,
`agent.tool`, or `agent.capture.profile` to Collector self-metrics.

## Shutdown

Stop the upstream stack without deleting volumes:

```sh
docker compose \
  -f .vendor/signoz/deploy/docker/docker-compose.yaml \
  -f compose/docker-compose.signoz.override.yml \
  down
```

Do not commit `.vendor/signoz`, ClickHouse data, SQLite files, tokens, or local
environment files.

## Source Notes

- Official SigNoz Docker install: https://signoz.io/docs/install/docker/
- SigNoz retention guide: https://signoz.io/docs/userguide/retention-period/
