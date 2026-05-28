# AOTEL-005 Completion Note

## Summary

Implemented the authenticated Nginx OTLP/HTTP ingress contract:

- allows only `/v1/logs`, `/v1/traces`, and `/v1/metrics`
- requires `auth_request /_auth` before proxying telemetry to the Collector
- sends auth subrequests to `auth-api` without forwarding OTLP payload bodies
- overwrites all `X-Telemetry-*` identity headers with auth-api response values
- forwards source IP through ingress-controlled `X-Telemetry-Source-Ip`
- returns `200` for `/healthz` and `404` for all other paths
- documents TLS, Collector, SigNoz, and header trust-boundary expectations

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
12 passed in 0.05s
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
