# Onboarding

Target: onboard a teammate and confirm baseline telemetry within five minutes
after the gateway is running.

Status: this is the planned onboarding interface. The `make` targets and
installers become runnable in Milestones 1 through 3.

## Operator Flow

```sh
make signoz-up
make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
```

The token command prints Codex and Claude Code snippets. The operator sends the
token to the teammate through an approved secret channel.

## Teammate Flow

1. Install the relevant agent tool.
2. Apply the generated Codex config or Claude env file.
3. Run the agent tool.
4. Confirm data in SigNoz with filters for:
   - `telemetry.user.email`
   - `telemetry.team.id`
   - `agent.tool`

## Codex Config Target

Write Codex telemetry config to user-level `~/.codex/config.toml`. The
installer must back up the existing file before writing:

```sh
cp ~/.codex/config.toml ~/.codex/config.toml.bak.$(date +%Y%m%d%H%M%S)
```

Target generated block:

```toml
[otel]
environment = "team-trial"
log_user_prompt = false

[otel.exporter.otlp-http]
endpoint = "https://otel.yourcompany.com/v1/logs"
protocol = "binary"

[otel.exporter.otlp-http.headers]
Authorization = "Bearer <TOKEN>"

[otel.metrics_exporter.otlp-http]
endpoint = "https://otel.yourcompany.com/v1/metrics"
protocol = "binary"

[otel.metrics_exporter.otlp-http.headers]
Authorization = "Bearer <TOKEN>"

[otel.trace_exporter.otlp-http]
endpoint = "https://otel.yourcompany.com/v1/traces"
protocol = "binary"

[otel.trace_exporter.otlp-http.headers]
Authorization = "Bearer <TOKEN>"
```

Implementation note: before coding the installer, verify this block against the
current installed Codex CLI and official Codex configuration docs, then validate
the rendered TOML with a parser. The project requirement is to generate this
shape, but Codex config keys may move between CLI releases.

For content capture investigations, generate an explicit overlay that changes
only:

```toml
[otel]
log_user_prompt = true
```

Do not enable prompt capture in the normal profile.

## Claude Code Default Env

Default Claude Code onboarding enables baseline telemetry without prompt,
tool-content, or raw API body capture:

```sh
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.yourcompany.com
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <TOKEN>"
```

Generate this as `templates/claude.env`.

## Claude Code Max Capture Env

Raw API body capture is opt-in only. Put it in `templates/claude.max-capture.env`
with a warning that it can include full request and response bodies,
conversation history, and sensitive data.

```sh
export OTEL_LOG_USER_PROMPTS=1
export OTEL_LOG_TOOL_DETAILS=1
export OTEL_LOG_TOOL_CONTENT=1
export OTEL_LOG_RAW_API_BODIES=1
```

Use max capture only for short forensic windows. Pair it with a short-lived
token whose `capture_profile` is `max`.

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
