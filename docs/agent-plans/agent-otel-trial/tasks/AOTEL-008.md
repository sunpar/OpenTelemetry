# AOTEL-008: SigNoz Bootstrap

## Objective

Add local SigNoz bootstrap files and documentation while keeping ingestion
private to the gateway network.

## Context To Load

- `docs/architecture.md`
- `docs/storage-retention.md`
- `docs/operating.md`

## Read Set

- `docs/storage-retention.md`
- `docs/operating.md`

## Write Set

- `compose/docker-compose.signoz.yml`
- `infra/signoz/README.md`

## Dependencies

None.

## Non-Goals

- Do not implement Kubernetes or Terraform.
- Do not add a second warehouse.

## Implementation Steps

1. Choose wrapper or pinned official SigNoz Compose strategy.
2. Document startup, shutdown, UI access, and retention checks.
3. Keep OTLP ingestion on internal networks only.

## Tests To Write First

- Compose config validation.
- Port exposure assertion.

## Verification Commands

```sh
docker compose -f compose/docker-compose.signoz.yml config
git diff --check
```

## Acceptance Criteria

- `make signoz-up` can start SigNoz after Makefile integration.
- SigNoz UI access is documented.
- SigNoz OTLP ingestion is not exposed to teammates.

## Review Focus

- Port exposure.
- Retention guidance.
- Avoiding vendor sprawl.

## Rollback Notes

Remove SigNoz Compose and docs.
