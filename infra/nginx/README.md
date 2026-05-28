# Nginx Ingress

This config is the local authenticated OTLP/HTTP ingress for the Agent
OpenTelemetry trial.

## Request Contract

Only these paths are accepted and proxied to the Collector:

- `/v1/logs`
- `/v1/traces`
- `/v1/metrics`

Every accepted OTLP request must pass the `auth_request` subrequest at
`/_auth`. The auth subrequest sends the bearer token to `auth-api` without
forwarding the OTLP payload body.

## Trust Boundary

Clients are trusted only for `Authorization: Bearer <token>`. Client-supplied
`X-Telemetry-*` headers are overwritten before proxying to the Collector.
`auth-api` is the source of user, team, token, and capture-profile identity.

Source IP is forwarded as `X-Telemetry-Source-Ip` from Nginx-controlled
`$remote_addr`. The config can honor `X-Forwarded-For` only from configured
private/internal proxy ranges through Nginx real-IP handling; it does not append
or forward an arbitrary client-provided chain.

## Deployment Notes

The Collector and SigNoz ingestion ports must stay private to the Docker
network or private subnet. Teammates should send telemetry only to this
authenticated gateway.

Terminate TLS in front of this Nginx server for production. Caddy or an
existing load balancer can own certificates; this local config intentionally
does not implement TLS automation.
