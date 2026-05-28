# AOTEL-010: Codex Onboarding Generator

## Objective

Implement Codex config template and installer that backs up user config and
applies content-minimal OpenTelemetry settings.

## Context To Load

- `docs/onboarding.md`
- `docs/storage-retention.md`

## Read Set

- `docs/onboarding.md`

## Write Set

- `templates/codex.config.toml`
- `scripts/install-codex-otel.sh`
- `scripts/backup-codex-config.sh`

## Dependencies

None.

## Non-Goals

- Do not enable prompt capture by default.
- Do not rewrite unrelated Codex settings.

## Implementation Steps

1. Create parseable Codex TOML template.
2. Implement timestamped config backup helper.
3. Install or replace only the managed OTel block.
4. Support endpoint and token arguments.
5. Keep max-capture prompt logging as an explicit overlay.

## Tests To Write First

- TOML template parse test.
- Installer preserves unrelated config.
- Installer creates timestamped backup.

## Verification Commands

```sh
shellcheck scripts/install-codex-otel.sh scripts/backup-codex-config.sh
git diff --check
```

## Acceptance Criteria

- Existing `~/.codex/config.toml` is backed up.
- Normal profile sets `log_user_prompt=false`.
- Rendered TOML parses.

## Review Focus

- Config preservation.
- Prompt logging defaults.
- Token handling.

## Rollback Notes

Remove Codex template and installer scripts.
