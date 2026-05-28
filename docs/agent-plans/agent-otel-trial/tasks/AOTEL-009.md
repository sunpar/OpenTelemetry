# AOTEL-009: Smoke And Security Verification Scripts

## Objective

Implement smoke scripts that send test telemetry and verify auth, header trust,
source IP, and direct-ingestion protections.

## Context To Load

- `docs/milestones.md`
- `docs/operating.md`
- `docs/troubleshooting.md`

## Read Set

- `compose/docker-compose.gateway.yml`
- `Makefile`
- `docs/milestones.md`

## Write Set

- `scripts/smoke-test-otel.py`
- `scripts/send-test-log.py`
- `docs/operating.md`
- `docs/troubleshooting.md`

## Dependencies

- `AOTEL-007`
- `AOTEL-010`
- `AOTEL-011`
- `AOTEL-012`

## Non-Goals

- Do not depend on production endpoints.
- Do not store real tokens in repo.

## Implementation Steps

1. Implement a minimal OTLP/HTTP test log sender.
2. Verify invalid token returns 401.
3. Verify all three OTLP signal paths require auth.
4. Verify spoofed `X-Telemetry-*` headers are overwritten.
5. Verify direct Collector and SigNoz OTLP host ports are unavailable.
6. Update operations docs with exact commands.

## Tests To Write First

- Unit tests for CLI flags and endpoint path construction.
- Integration smoke test against local Compose stack.

## Verification Commands

```sh
make smoke TOKEN=<issued-token>
git diff --check
```

## Acceptance Criteria

- Milestone 1 acceptance criteria are executable.
- Valid token reaches Collector/SigNoz.
- Invalid token and direct-ingestion paths fail.

## Review Focus

- Security assertions.
- No real tokens.
- Clear failure output.

## Rollback Notes

Remove smoke scripts and revert operations doc changes.
