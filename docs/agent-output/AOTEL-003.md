# AOTEL-003 Completion Note

## Summary

Implemented the auth-api verification endpoint:

- FastAPI `/auth/verify` for Nginx `auth_request`
- 401 for missing, malformed, unknown, and hash-mismatch tokens
- 403 for revoked, expired, disabled-user, and scope-mismatch tokens
- 204 plus trusted `X-Telemetry-*` headers for valid tokens
- audit rows using `X-Original-URI`, `X-Original-Content-Length`, and
  `X-Telemetry-Source-Ip`
- no public token or user admin routes
- settings support for `AUTH_API_DB_PATH` and `AUTH_DB_PATH`
- Dockerfile for the future Compose runtime

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest services/auth-api/tests -q
```

Result:

```text
14 passed, 1 warning in 0.18s
```

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
52 passed, 1 warning in 0.57s
```

```sh
git diff --check
```

Result: clean.

## Deviations

- The FastAPI `TestClient` emits a Starlette warning about `httpx`; tests pass
  and no runtime behavior is affected.

## Risks

- Runtime Docker image validation is deferred to AOTEL-007 when Compose exists.
