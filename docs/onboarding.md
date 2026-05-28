# Onboarding

The onboarding goal is to get a teammate sending useful telemetry in under five
minutes after the gateway is running.

## Operator Flow

```sh
make signoz-up
make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
```

The token command should print ready-to-use snippets for Codex and Claude Code.
The operator sends the token to the teammate through an approved secret channel.

## Teammate Flow

1. Install the relevant agent tool.
2. Apply the generated Codex config or Claude env file.
3. Run the agent tool.
4. Confirm data in SigNoz with filters for:
   - `telemetry.user.email`
   - `telemetry.team.id`
   - `agent.tool`

## Codex Config Target

Codex telemetry config should be written to user-level `~/.codex/config.toml`.
The installer must back up the existing file before writing:

```sh
cp ~/.codex/config.toml ~/.codex/config.toml.bak.$(date +%Y%m%d%H%M%S)
```

Target generated block:

```toml
[otel]
environment = "team-trial"
log_user_prompt = true
exporter = { otlp-http = {
  endpoint = "https://otel.yourcompany.com/v1/logs",
  protocol = "binary",
  headers = { "Authorization" = "Bearer <TOKEN>" }
}}
metrics_exporter = { otlp-http = {
  endpoint = "https://otel.yourcompany.com/v1/metrics",
  protocol = "binary",
  headers = { "Authorization" = "Bearer <TOKEN>" }
}}
trace_exporter = { otlp-http = {
  endpoint = "https://otel.yourcompany.com/v1/traces",
  protocol = "binary",
  headers = { "Authorization" = "Bearer <TOKEN>" }
}}
```

Implementation note: before coding the installer, verify this block against the
current installed Codex CLI and official Codex configuration docs. The project
requirement is to generate this shape, but Codex config keys may move between
CLI releases.

## Claude Code Default Env

Default Claude Code onboarding should enable useful telemetry without raw API
body capture:

```sh
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.yourcompany.com
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <TOKEN>"
export OTEL_LOG_USER_PROMPTS=1
export OTEL_LOG_TOOL_DETAILS=1
export OTEL_LOG_TOOL_CONTENT=1
```

This should be generated as `templates/claude.env`.

## Claude Code Max Capture Env

Raw API body capture is opt-in only. Put it in `templates/claude.max-capture.env`
with a clear warning that it can include full request and response bodies,
conversation history, and sensitive data.

```sh
export OTEL_LOG_RAW_API_BODIES=1
```

Use max capture for short forensic windows, not normal team onboarding.

## Installer Requirements

### `install-codex-otel.sh`

- Accept `--endpoint` and `--token`.
- Back up `~/.codex/config.toml` if it exists.
- Create `~/.codex` if it does not exist.
- Append or replace only the managed OTel block.
- Preserve unrelated Codex settings.
- Print the backup path and resulting endpoint.

### `install-claude-otel.sh`

- Accept `--endpoint`, `--token`, and optional `--profile normal|max`.
- Write a shell-compatible env file.
- Avoid modifying shell startup files unless a flag explicitly asks for it.
- Print the command to source the generated file.

## Verification

After onboarding, run a small agent action and confirm:

- SigNoz receives at least one event or span.
- `telemetry.user.email` matches the issued token owner.
- `telemetry.team.id` matches the user's team.
- `telemetry.token.id` matches the issued token id.
- `agent.tool` is `codex` or `claude_code`.

## Source Notes

- Claude Code monitoring and OpenTelemetry env vars: https://code.claude.com/docs/en/monitoring-usage
- Codex docs landing page: https://developers.openai.com/codex
