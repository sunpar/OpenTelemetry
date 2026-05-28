# AOTEL-005: Nginx Authenticated OTLP Ingress

## Objective

Add Nginx config for authenticated OTLP/HTTP ingress using `auth_request` and
trusted telemetry headers.

## Context To Load

- `docs/architecture.md`
- `docs/troubleshooting.md`

## Read Set

- `docs/architecture.md`
- `docs/troubleshooting.md`

## Write Set

- `infra/nginx/nginx.conf`
- `infra/nginx/README.md`

## Dependencies

None.

## Non-Goals

- Do not implement TLS automation.
- Do not expose direct Collector or SigNoz ingestion.

## Implementation Steps

1. Allow only `/v1/logs`, `/v1/traces`, and `/v1/metrics`.
2. Add internal `/_auth` subrequest.
3. Overwrite `X-Telemetry-*` headers from auth-api responses.
4. Set trusted source IP header from socket or trusted proxy chain.
5. Return 404 for other paths and 200 for `/healthz`.

## Tests To Write First

- Config text test for allowed paths and `auth_request`.
- Config text test that `proxy_set_header` overwrites trusted headers.

## Verification Commands

```sh
git diff --check
```

## Acceptance Criteria

- Only documented OTLP paths proxy to Collector.
- `auth_request` is required on every OTLP path.
- Client-supplied identity headers cannot pass through.

## Review Focus

- Header trust boundary.
- Payload preservation.
- Path allowlist.

## Rollback Notes

Remove `infra/nginx` files.
