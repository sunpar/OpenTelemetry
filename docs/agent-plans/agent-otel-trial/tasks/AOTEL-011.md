# AOTEL-011: Claude Code Onboarding Generator

## Objective

Implement Claude Code env templates and installer with content-minimal defaults
and explicit max-capture profile.

## Context To Load

- `docs/onboarding.md`
- `docs/storage-retention.md`

## Read Set

- `docs/onboarding.md`

## Write Set

- `templates/claude.env`
- `templates/claude.max-capture.env`
- `scripts/install-claude-otel.sh`

## Dependencies

None.

## Non-Goals

- Do not modify shell startup files by default.
- Do not enable raw API body logging by default.

## Implementation Steps

1. Create normal Claude env template.
2. Create max-capture env overlay.
3. Implement installer that writes env file and prints source command.
4. Support endpoint, token, and profile arguments.

## Tests To Write First

- Shell syntax test for generated env.
- Installer normal profile excludes prompt, tool, and raw body capture.
- Max profile includes explicit capture flags.

## Verification Commands

```sh
shellcheck scripts/install-claude-otel.sh
git diff --check
```

## Acceptance Criteria

- Normal env includes OTLP exporters and bearer auth.
- Normal env excludes prompt/tool/raw body capture.
- Max env includes explicit high-capture flags.

## Review Focus

- Safe defaults.
- Shell compatibility.
- No startup-file mutation by default.

## Rollback Notes

Remove Claude templates and installer.
