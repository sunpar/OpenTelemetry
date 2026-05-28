# AOTEL-002: Auth Storage And Token Primitives

## Objective

Implement SQLite schema, user/token models, token generation, hashing, parsing,
revocation, expiry, scopes, capture profile, and audit helpers.

## Context To Load

- `docs/token-model.md`
- `docs/agent-context/architecture-index.md`
- `docs/agent-plans/agent-otel-trial/acceptance-tests.md`

## Read Set

- `services/auth-api/pyproject.toml`
- `docs/token-model.md`

## Write Set

- `services/auth-api/src/db.py`
- `services/auth-api/src/models.py`
- `services/auth-api/src/tokens.py`
- `services/auth-api/migrations/`
- `services/auth-api/tests/test_tokens.py`
- `services/auth-api/tests/test_db.py`

## Dependencies

- `AOTEL-001`

## Non-Goals

- Do not implement HTTP routes.
- Do not implement CLI UX.

## Implementation Steps

1. Create schema migration matching `docs/token-model.md`.
2. Implement token id parsing and random secret generation.
3. Store only token hashes, prefixes, and last four characters.
4. Implement constant-time token verification helpers.
5. Implement audit insert helpers without request bodies.

## Tests To Write First

- Token format parse/generate tests.
- Hash mismatch, revoked, expired, disabled-user, and scope tests.
- Audit row creation test.

## Verification Commands

```sh
git diff --check
python -m pytest services/auth-api/tests
```

## Acceptance Criteria

- Schema includes users, tokens, and ingest_audit fields from docs.
- Token secrets are never stored in plaintext.
- Validation distinguishes accepted and rejected states.
- `capture_profile` defaults to `normal`.

## Review Focus

- Secret handling.
- Constant-time compare.
- SQLite-to-Postgres portability.

## Rollback Notes

Revert auth storage files and migration. No production data exists yet.
