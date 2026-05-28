# AOTEL-005 Completion Note

## Summary

Implemented the authenticated Nginx OTLP/HTTP ingress contract:

- allows only `/v1/logs`, `/v1/traces`, and `/v1/metrics`
- requires `auth_request /_auth` before proxying telemetry to the Collector
- sends auth subrequests to `auth-api` without forwarding OTLP payload bodies
- sends normalized path, method, content length, and source IP to `auth-api`
- disables client header passthrough to the Collector and re-adds only OTLP
  transport headers plus trusted auth-api metadata
- forwards source IP through ingress-controlled `X-Telemetry-Source-Ip`
- allows OTLP payloads up to 32 MiB
- returns `200` for `/healthz` and `404` for all other paths
- documents TLS, Collector, SigNoz, and header trust-boundary expectations

## Verification

Run from the PR worktree:

```sh
uvx --python 3.11 pytest -q
```

Result:

```text
14 passed in 0.07s
```

```sh
docker run --rm --add-host auth-api:127.0.0.1 --add-host otel-collector:127.0.0.1 -v "$PWD/infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:1.27-alpine nginx -t
```

Result:

```text
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

```sh
git diff --check
```

Result: clean.

## Deviations

None.

## Risks

- Config syntax has text-level coverage only. Runtime validation against an
  Nginx container will be added when Compose exists in AOTEL-007.
