# Token Model

Use opaque bearer tokens, not JWTs. Opaque tokens make revocation, expiration,
and team/user edits server-authoritative at request time.

## Token Format

```text
aotel_live_tok_01JYABCDEF1234567890_<random-secret>
```

The public token id is the `tok_...` segment. The secret is random. Store only a
hash of the full token or secret, plus a prefix and last four characters for
operator display.

## Minimum Schema

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  team_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);

CREATE TABLE tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT,
  token_hash TEXT NOT NULL,
  token_prefix TEXT NOT NULL,
  token_last4 TEXT NOT NULL,
  scopes TEXT NOT NULL DEFAULT 'logs,traces,metrics',
  capture_profile TEXT NOT NULL DEFAULT 'normal',
  expires_at TEXT,
  revoked_at TEXT,
  created_at TEXT NOT NULL,
  last_seen_at TEXT
);

CREATE TABLE ingest_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token_id TEXT,
  user_id TEXT,
  team_id TEXT,
  path TEXT,
  content_length INTEGER,
  status_code INTEGER,
  remote_addr TEXT,
  created_at TEXT NOT NULL
);
```

SQLite is enough for the team trial. Keep schema and data access narrow enough
that Postgres can replace SQLite without changing callers.

## Validation Flow

1. Read `Authorization: Bearer <token>`.
2. Parse the public token id.
3. Look up the token id.
4. Constant-time compare the provided token hash with the stored hash.
5. Reject revoked tokens.
6. Reject expired tokens.
7. Reject tokens whose user is disabled.
8. Optionally validate that the requested signal path is allowed by token
   scopes.
9. Update `last_seen_at` and write an `ingest_audit` row.
10. Return `204` with identity headers.

## Auth Response Headers

```http
X-Telemetry-User: alice@example.com
X-Telemetry-Team: quant-dev
X-Telemetry-User-Id: usr_...
X-Telemetry-Token-Id: tok_...
X-Telemetry-Capture-Profile: normal
```

Nginx must copy these response headers into trusted proxy headers for the
Collector. Client-supplied values for these same headers must be overwritten.
Ingress should also set `X-Telemetry-Source-Ip` from the socket or trusted proxy
chain, not from an arbitrary client-supplied header.

## CLI Contract

The first control-plane surface is `otelctl`, not a public admin UI.

```sh
otelctl users add --email alice@example.com --team quant-dev --name "Alice"
otelctl tokens issue --email alice@example.com --name "alice-mbp-codex" --expires 90d
otelctl tokens list --email alice@example.com
otelctl tokens revoke --token-id tok_01J...
otelctl users disable --email alice@example.com
```

The token issuance command should print:

- the newly issued token once
- a Codex config snippet
- a Claude Code env snippet
- a reminder that raw Claude API body capture is opt-in only

Tokens default to `capture_profile=normal`. Max-capture tokens should be
explicitly named, short-lived, and issued only for a bounded investigation.

## Status Codes

| Condition | Status |
| --- | ---: |
| Missing bearer token | 401 |
| Malformed token | 401 |
| Unknown token id | 401 |
| Hash mismatch | 401 |
| Revoked token | 403 |
| Expired token | 403 |
| Disabled user | 403 |
| Scope not allowed for signal path | 403 |
| Valid token | 204 |

## Audit Requirements

Write an audit row for accepted and rejected requests when a token id can be
parsed. Include the request path, status code, remote address, content length,
token id, user id, and team id when known. Do not store request bodies in the
auth database.
