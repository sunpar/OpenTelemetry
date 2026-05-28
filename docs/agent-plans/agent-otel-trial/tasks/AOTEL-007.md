# AOTEL-007: Gateway Compose Stack And Make Targets

## Objective

Wire auth-api, Nginx, and Collector together with Compose and Make targets for
local trial operations.

## Context To Load

- `docs/architecture.md`
- `docs/operating.md`
- `docs/agent-context/test-commands.md`

## Read Set

- `Makefile`
- `.env.example`
- `services/auth-api/Dockerfile`
- `infra/nginx/nginx.conf`
- `infra/otel/collector.local.yaml`
- `compose/docker-compose.signoz.yml`

## Write Set

- `compose/docker-compose.gateway.yml`
- `Makefile`
- `.env.example`

## Dependencies

- `AOTEL-001`
- `AOTEL-003`
- `AOTEL-004`
- `AOTEL-005`
- `AOTEL-006`
- `AOTEL-008`

## Non-Goals

- Do not expose SigNoz or Collector OTLP ports directly to host.
- Do not implement production TLS.

## Implementation Steps

1. Define auth-api, nginx, and otel-collector services.
2. Join gateway services to the SigNoz network without publishing internal
   ingestion ports.
3. Wire Make targets: `up`, `down`, `logs`, `user`, `token`, `smoke`,
   `signoz-up`.
4. Document environment variables in `.env.example`.

## Tests To Write First

- Compose config validation.
- Port exposure assertion for Collector and SigNoz ingestion.

## Verification Commands

```sh
docker compose -f compose/docker-compose.gateway.yml config
git diff --check
```

## Acceptance Criteria

- `make up` starts gateway stack.
- `make user` and `make token` execute `otelctl` in auth-api context.
- Collector and SigNoz OTLP ports are not host-published.

## Review Focus

- Docker network boundaries.
- No secret defaults.
- Make target accuracy.

## Rollback Notes

Revert Compose, Makefile, and env changes.
