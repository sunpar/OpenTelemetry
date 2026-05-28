# SigNoz Bootstrap

Use the official SigNoz Docker Compose stack for the local backend and keep this
repository focused on the gateway, auth, onboarding, and dashboard artifacts.

The repo-owned `compose/docker-compose.signoz.yml` file is a small wrapper
contract. It validates the shared network name and confirms this repo does not
publish SigNoz OTLP ingestion ports itself.

## Local Startup

Clone the upstream SigNoz deploy files under the ignored vendor directory:

```sh
git clone -b main https://github.com/SigNoz/signoz.git .vendor/signoz
```

Start the official Docker stack:

```sh
docker compose -f .vendor/signoz/deploy/docker/docker-compose.yaml up -d --remove-orphans
```

Check this repo's wrapper contract:

```sh
docker compose -f compose/docker-compose.signoz.yml config
```

After AOTEL-007 wires the Makefile, `make signoz-up` should run the same
startup path or call a pinned equivalent.

## UI Access

For a local trial, open:

```text
http://localhost:8080
```

Keep UI access limited to localhost or an authenticated internal network.

## Private Ingestion

Do not expose SigNoz OTLP ports to teammates. External telemetry must enter
through the authenticated gateway:

```text
client -> Nginx auth ingress -> Collector gateway -> SigNoz
```

The official SigNoz Docker stack may publish `4317` and `4318` for standalone
use. For this product, keep those ports bound to localhost, firewalled, or
removed by an override before team access. The gateway Collector should reach
SigNoz over the Docker network using `signoz-otel-collector:4317`.

## Retention Checks

Review retention in the SigNoz UI before onboarding teammates. Use the baseline
policy in `docs/storage-retention.md`:

- logs and traces: short hot retention for the trial
- metrics: longer retention than logs/traces
- raw API body events: disabled by default

Check disk growth during the first week and shorten retention before enabling
any max-capture profile.

## Shutdown

Stop the upstream stack without deleting volumes:

```sh
docker compose -f .vendor/signoz/deploy/docker/docker-compose.yaml down
```

Do not commit `.vendor/signoz`, ClickHouse data, SQLite files, tokens, or local
environment files.

## Source Notes

- Official SigNoz Docker install: https://signoz.io/docs/install/docker/
- SigNoz retention guide: https://signoz.io/docs/userguide/retention-period/
