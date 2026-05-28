# AOTEL-004: otelctl User And Token CLI

## Objective

Implement local operator CLI commands for user creation, token issuance/listing,
token revocation, and user disable.

## Context To Load

- `docs/token-model.md`
- `docs/onboarding.md`

## Read Set

- `services/auth-api/src/db.py`
- `services/auth-api/src/tokens.py`
- `cli/otelctl/pyproject.toml`

## Write Set

- `cli/otelctl/src/otelctl.py`
- `cli/otelctl/tests/test_otelctl.py`

## Dependencies

- `AOTEL-002`

## Non-Goals

- Do not add a public admin UI.
- Do not print token secrets after issuance.

## Implementation Steps

1. Implement `users add`.
2. Implement `tokens issue`, `tokens list`, and `tokens revoke`.
3. Implement `users disable`.
4. Print Codex and Claude Code snippets on token issuance.
5. Support expiry duration parsing.

## Tests To Write First

- CLI creates user and issues token.
- Token secret appears only once.
- Revoke and disable commands change validation outcomes.

## Verification Commands

```sh
git diff --check
python -m pytest cli/otelctl/tests
```

## Acceptance Criteria

- Commands match `docs/token-model.md`.
- Token issue prints snippets from onboarding contract.
- List output shows token prefix/last4 but not secret.

## Review Focus

- Secret redaction.
- Exit codes and error messages.
- DB path configuration.

## Rollback Notes

Revert CLI files. Auth storage remains.
