# Troubleshooting

Use this guide to separate auth failures, ingress routing failures, Collector
pipeline failures, and SigNoz visibility issues.

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
```

Inspect auth-api logs:

```sh
docker compose -f compose/docker-compose.gateway.yml logs auth-api
```

## Request Fails With 403

Likely causes:

- Token was revoked.
- Token expired.
- User is disabled.
- Token scopes do not allow the requested signal.

Checks:

```sh
otelctl tokens list --email alice@example.com
```

Confirm `revoked_at`, `expires_at`, user status, and scopes.

## Request Fails With 404

Only these paths are allowed:

```text
/v1/logs
/v1/traces
/v1/metrics
```

Any other path returns 404.

## Request Succeeds But No Identity Fields In SigNoz

Likely causes:

- Nginx did not copy auth response headers.
- Nginx did not overwrite spoofed client headers.
- Ingress is trusting client-supplied source IP headers.
- Collector OTLP/HTTP receiver is missing `include_metadata: true`.
- Collector resource processor keys do not match header metadata names.
- The request bypassed ingress and posted directly to the Collector or SigNoz.

Checks:

- Review `infra/nginx/nginx.conf`.
- Review `infra/otel/collector.local.yaml`.
- Confirm Collector receives traffic only from ingress.
- Send a test log through Nginx, not directly to Collector.

## Request Reaches Collector But Not SigNoz

Likely causes:

- SigNoz is not running.
- Collector cannot resolve `signoz-otel-collector`.
- Exporter queue is full.
- Exporter retries are exhausted.
- Docker networks are not joined correctly.

Checks:

```sh
docker compose -f compose/docker-compose.gateway.yml logs otel-collector
docker compose -f compose/docker-compose.gateway.yml ps
```

Inspect Collector health metrics and exporter logs.

## SigNoz Shows Data Without User Or Team

Treat this as a security and data quality issue. It means telemetry bypassed the
trusted identity path or enrichment failed.

Actions:

1. Close direct external access to SigNoz OTLP ports.
2. Close direct external access to Collector OTLP ports.
3. Verify Nginx overwrites `X-Telemetry-*` headers.
4. Verify Collector `resource/tenant_from_headers` processor is in every signal
   pipeline.
5. Verify `telemetry.source.ip` comes from ingress-controlled source IP logic,
   not from arbitrary client `X-Forwarded-For`.
6. Re-run the smoke test with a valid token.

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
docs before shipping the installer.

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
5. Check Collector queue metrics and ingress logs.

## Token Revocation Does Not Take Effect

Check opaque tokens server-side on every request. If revoked tokens continue to
work:

- Confirm Nginx calls `/_auth` on every OTLP path.
- Confirm auth-api reads current DB state for every validation.
- Confirm there is no success cache at ingress.
- Confirm the client is not using a different valid token.
- Confirm audit rows show the expected token id.
