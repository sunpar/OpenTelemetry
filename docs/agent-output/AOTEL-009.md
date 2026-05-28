# AOTEL-009 Completion

## Changes

- Added `scripts/send-test-log.py` for sending one OTLP/HTTP JSON test log through the authenticated gateway.
- Added `scripts/smoke-test-otel.py` for local smoke and security checks.
- Covered invalid-token rejection across `/v1/logs`, `/v1/traces`, and `/v1/metrics`.
- Exercised the valid-token path with spoofed `X-Telemetry-*` and `X-Forwarded-For` headers so the Nginx overwrite path is used.
- Checked that direct host ingestion ports `127.0.0.1:4318` and `127.0.0.1:4317` are unavailable.
- Updated operating and troubleshooting docs with the exact smoke commands and direct-ingestion failure mode.

## Verification

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_aotel009_smoke_scripts.py -q
# 4 passed, 1 skipped in 0.01s

python3 -m py_compile scripts/smoke-test-otel.py scripts/send-test-log.py
# no output

make up
# auth-api, nginx, and otel-collector started

make user EMAIL=smoke@example.com TEAM=trial NAME="Smoke Test"
# created/updated smoke@example.com

make token EMAIL=smoke@example.com TOKEN_NAME=smoke EXPIRES=1d ENDPOINT=http://localhost:8088
# issued temporary local token

make smoke TOKEN=<issued-token> ENDPOINT=http://localhost:8088
# invalid tokens rejected on logs/traces/metrics
# valid log accepted on /v1/logs with status=200
# direct ingestion ports 127.0.0.1:4318 and 127.0.0.1:4317 unavailable
# smoke checks passed

make down
# gateway containers and network removed

git diff --check
# no output
```

## Risks And Deviations

- The live smoke test proves the ingress and direct-port behavior locally, but SigNoz was not started for this run. The Collector accepted the log and queued/exported according to its configured backend path.
- The spoofed-header check exercises the Nginx overwrite route but does not query SigNoz to inspect the final enriched resource attributes. SigNoz validation remains part of the manual Milestone 1 acceptance path after `make signoz-up`.
