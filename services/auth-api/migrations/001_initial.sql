CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  team_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
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

CREATE TABLE IF NOT EXISTS ingest_audit (
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

CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_ingest_audit_token_id ON ingest_audit(token_id);
CREATE INDEX IF NOT EXISTS idx_ingest_audit_created_at ON ingest_audit(created_at);
