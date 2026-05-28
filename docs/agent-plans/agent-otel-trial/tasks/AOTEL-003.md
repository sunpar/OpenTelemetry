# AOTEL-003: Auth API Verification Endpoint

## Objective

Expose a FastAPI verification endpoint that validates bearer tokens and returns
trusted telemetry headers for Nginx `auth_request`.

## Context To Load

- `docs/token-model.md`
- `docs/architecture.md`
- `docs/troubleshooting.md`

## Read Set

- `services/auth-api/src/db.py`
- `services/auth-api/src/tokens.py`
- `docs/token-model.md`

## Write Set

- `services/auth-api/src/app.py`
- `services/auth-api/src/settings.py`
- `services/auth-api/Dockerfile`
- `services/auth-api/tests/test_auth_api.py`

## Dependencies

- `AOTEL-002`

## Non-Goals

- Do not expose public admin endpoints.
- Do not implement token issuance over HTTP.

## Implementation Steps

1. Add `/auth/verify` for Nginx subrequests.
2. Return 204 and trusted headers for valid tokens.
3. Return 401 or 403 according to failure mode.
4. Record ingest audit details when token id is parseable.
5. Add Dockerfile for Compose runtime.

## Tests To Write First

- Missing, malformed, and unknown token return 401.
- Revoked, expired, and disabled-user tokens return 403.
- Valid token returns trusted headers and 204.

## Verification Commands

```sh
git diff --check
python -m pytest services/auth-api/tests
```

## Acceptance Criteria

- Valid requests include all documented `X-Telemetry-*` headers.
- No admin issuance endpoint is public.
- Audit rows do not store request bodies.

## Review Focus

- HTTP status correctness.
- Header names matching Nginx and Collector docs.
- No public admin surface.

## Rollback Notes

Revert auth API files. Storage primitives remain usable by CLI.
