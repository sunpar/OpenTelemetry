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

Clients are trusted only for `Authorization: Bearer <token>`, and that token is
sent only to `auth-api`. The Collector hop disables client header passthrough
and re-adds only OTLP transport headers plus trusted `X-Telemetry-*` metadata
from `auth-api`.

Source IP is forwarded as `X-Telemetry-Source-Ip` from Nginx-controlled
`$remote_addr`. Real-IP handling is disabled by default so client-supplied
`X-Forwarded-For` cannot rewrite the source address. Deployments behind a load
balancer may enable Nginx real-IP handling only for exact proxy addresses, not
broad private address ranges.

The auth subrequest forwards normalized request metadata with
`X-Original-URI`, `X-Original-Method`, `X-Original-Content-Length`, and
`X-Telemetry-Source-Ip` so `auth-api` can enforce signal scopes and audit the
original OTLP request.

## Deployment Notes

The Collector and SigNoz ingestion ports must stay private to the Docker
network or private subnet. Teammates should send telemetry only to this
authenticated gateway.

Terminate TLS in front of this Nginx server for production. Caddy or an
existing load balancer can own certificates; this local config intentionally
does not implement TLS automation.
