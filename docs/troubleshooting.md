# Troubleshooting

Use this guide to separate token failures, native gateway forwarding failures,
upstream backend failures, and client telemetry configuration issues.

## Request Fails With 401

Likely causes:

- Missing `Authorization` header.
- Header is not `Bearer <token>`.
- Token format is malformed.
- Token id cannot be parsed.
- Token id does not exist.
- Token hash comparison failed.

Checks:

```sh
curl -i http://localhost:8088/v1/logs
curl -i http://localhost:8088/v1/logs -H 'Authorization: Bearer invalid'
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
```

Inspect the foreground `make native-up` logs or the logs from the process
supervisor running the FastAPI app.

## Request Fails With 403

Likely causes:

- Token was revoked.
- Token expired.
- User is disabled.
- Token scopes do not allow the requested signal.

Checks:

```sh
PYTHONPATH=packages/auth-core/src:cli/otelctl/src \
  .venv/bin/python cli/otelctl/src/otelctl.py \
  --db-path ./auth-api.sqlite3 tokens list --email alice@example.com
```

Confirm `revoked_at`, `expires_at`, user status, and scopes.

## Request Fails With 404

Only these OTLP paths are allowed:

```text
/v1/logs
/v1/traces
/v1/metrics
```

Any other path returns 404.

## Request Fails With 413

The payload is larger than `AOTEL_GATEWAY_MAX_BODY_BYTES`. The default is 32 MiB.
Increase the setting only after confirming the upstream backend can handle the
same payload size.

## Request Fails With 502 Or 503

Likely causes:

- `AOTEL_OTLP_UPSTREAM` is unset.
- The upstream URL is wrong.
- The native Collector or managed OTLP endpoint is down.
- The managed OTLP endpoint requires `AOTEL_OTLP_UPSTREAM_AUTHORIZATION`.
- TLS or proxy settings between FastAPI and the upstream are incorrect.
- The upstream returned a network error while the gateway was forwarding.

Checks:

```sh
curl -fsS http://localhost:8088/healthz
printf '%s\n' "$AOTEL_OTLP_UPSTREAM"
test -n "$AOTEL_OTLP_UPSTREAM_AUTHORIZATION" && printf '%s\n' 'upstream authorization configured'
curl -i "$AOTEL_OTLP_UPSTREAM/v1/logs"
```

The last command may return an auth or content error from the upstream; that is
still useful because it proves the upstream is reachable.

## Request Succeeds But Identity Fields Are Wrong

Likely causes:

- The request bypassed the FastAPI gateway and posted directly to the upstream.
- The backend is reading client-supplied payload attributes instead of trusted
  gateway metadata.
- A downstream Collector config is not copying `X-Telemetry-*` headers into
  resource attributes.

Checks:

```sh
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
```

The smoke script sends spoofed `X-Telemetry-*` and `X-Forwarded-For` headers on
the valid log request. After the smoke run, inspect the backend and confirm:

- `telemetry.user.email` matches the issued token owner, not the spoofed header.
- `telemetry.team.id` matches the issued token team, not the spoofed header.
- `telemetry.token.id` matches the issued token id, not the spoofed header.
- `telemetry.source.ip` does not equal the spoofed `X-Forwarded-For` value.

## Backend Shows Data Without User Or Team

Treat this as a security and data quality issue. It means telemetry bypassed the
trusted identity path or downstream enrichment failed.

Actions:

1. Close direct external access to backend OTLP ingestion.
2. Route clients only through the FastAPI gateway.
3. Verify `auth_api.gateway` overwrites `X-Telemetry-*` headers.
4. If using a native Collector, verify its resource processor maps trusted
   gateway metadata into resource attributes.
5. Re-run the smoke test with a valid token.

## Dashboard Import Does Not Show Data

Import `infra/signoz/dashboards/agent-telemetry-collected-data.signoz.json`
only after the backend is initialized. The dashboard title is
`Agent Telemetry - Collected Data`.

Checks:

```sh
.venv/bin/python -m json.tool infra/signoz/dashboards/agent-telemetry-collected-data.signoz.json >/dev/null
AOTEL_SMOKE_TOKEN=<issued-token> make smoke
```

Then open the dashboard and check the service, user, team, tool, and
capture-profile variables. If panels are empty, confirm the smoke records exist
in the backend and select `unknown` for older data that predates normalized
agent attributes.

## Direct-Port Hardening Checks

The smoke script can optionally verify that direct OTLP ports are not reachable
from the current host:

```sh
AOTEL_SMOKE_TOKEN=<issued-token> \
  .venv/bin/python scripts/smoke-test-otel.py \
  --endpoint http://localhost:8088 \
  --check-direct-ports
```

Use this in production-like environments. For local development, a native
Collector may intentionally listen on `127.0.0.1:4318`, so the check is not part
of the default smoke target.

## Codex Does Not Emit Telemetry

Checks:

- Confirm the installed Codex version.
- Confirm the managed `[otel]` block is in user-level `~/.codex/config.toml`.
- Confirm the endpoint path is signal-specific:
  - `/v1/logs`
  - `/v1/metrics`
  - `/v1/traces`
- Confirm the `Authorization` header is present in each exporter config.
- Confirm the installer did not overwrite unrelated Codex config.

Re-verify Codex telemetry config against the installed CLI and official Codex
docs before shipping installer changes.

## Claude Code Does Not Emit Telemetry

Checks:

- Confirm the env file was sourced in the same shell that starts Claude Code.
- Confirm `CLAUDE_CODE_ENABLE_TELEMETRY=1`.
- Confirm OTLP exporters are set for logs, metrics, and traces.
- Confirm `OTEL_EXPORTER_OTLP_ENDPOINT` points to the gateway base URL.
- Confirm `OTEL_EXPORTER_OTLP_HEADERS` contains the bearer token.
- Check whether beta trace export requires `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`.

## Volume Grows Too Fast

Likely causes:

- Raw API body capture is enabled.
- Tool content logging is enabled for too many users.
- Retention is too long for current disk size.
- High-cardinality metric dimensions are being emitted.
- A client is retrying aggressively.

Actions:

1. Disable raw body capture.
2. Reduce max-capture users.
3. Review retention settings.
4. Review dashboards for expensive group-bys.
5. Check upstream request volume, latency, and storage growth.

## Token Revocation Does Not Take Effect

Tokens are checked server-side on every gateway request. If revoked tokens
continue to work:

- Confirm clients are sending telemetry through the FastAPI gateway.
- Confirm auth-api reads current DB state for every validation.
- Confirm there is no success cache in a parent FastAPI app or upstream proxy.
- Confirm the client is not using a different valid token.
- Confirm audit rows show the expected token id.
