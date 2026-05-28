# AOTEL-002 Completion Note

## Summary

Implemented auth storage and token primitives:

- SQLite migration for `users`, `tokens`, and `ingest_audit`
- user upsert and audit insert helpers
- opaque token generation using `aotel_live_tok_<id>_<secret>`
- token id parsing, token hashing, prefix/last4 storage, and revocation
- validation for hash mismatch, revoked, expired, disabled-user, and scope
  rejection states
- `capture_profile` defaulting to `normal` with max profile support
- audit rows for parseable accepted and rejected requests without request bodies

## Verification

Run from `/Users/sunpar/Documents/OpenTelemetry-worktrees/aotel-001-scaffold`:

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest services/auth-api/tests -q
```

Result:

```text
9 passed in 0.03s
```

```sh
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Result:

```text
47 passed in 0.36s
```

```sh
git diff --check
```

Result: clean.

## Deviations

- The auth tests insert `services/auth-api/src` into `sys.path` so they work
  both as targeted package tests and as part of the repo-root test suite.

## Risks

- Token hashing uses SHA-256 over high-entropy opaque tokens. That is suitable
  for random bearer tokens, but production hardening can add a server-side
  pepper before broader rollout.
