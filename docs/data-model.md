# Data Model

The data model starts with trusted tenant/user attributes plus a thin agent
normalization layer. Preserve native Codex and Claude Code fields in v1.
Normalize only the fields needed for cross-tool dashboards.

## Required Resource Attributes

| Attribute | Description |
| --- | --- |
| `telemetry.team.id` | Team or group that owns the user |
| `telemetry.user.id` | Internal user id from auth-api |
| `telemetry.user.email` | User email from auth-api |
| `telemetry.token.id` | Public token id used for ingestion |
| `telemetry.source.ip` | Source IP derived by ingress from a trusted socket or proxy chain |
| `agent.tool` | `codex`, `claude_code`, `cursor`, or `custom` |
| `agent.capture.profile` | `normal` or `max`, copied from trusted token metadata |
| `agent.client.version` | Client tool version when available |
| `agent.session.id` | Tool session id when available |
| `agent.conversation.id` | Conversation id when available |
| `repo.name` | Repository name when available |
| `repo.remote` | Repository remote URL when available |
| `git.branch` | Git branch when available |
| `git.commit` | Git commit SHA when available |
| `model.name` | Model identifier when available |
| `run.mode` | `interactive`, `exec`, `ci`, or `sdk` |
| `run.outcome` | `success`, `error`, `cancelled`, or `unknown` |

## Signal Guidance

### Logs

Logs can carry richer contextual fields, including prompts, tool arguments,
command strings, repo paths, file paths, and error details. These fields are
useful for search and drilldown but should not become default group-by fields
on high-volume dashboards.

### Traces

Traces should carry session, conversation, request, tool-call, model, repo, and
outcome fields when the client emits them. Traces are the best place to ask
questions like "what did Alice's Codex do today?" because they preserve
operation flow.

### Metrics

Metrics need stricter cardinality control. Team, user, tool, model, and capture
profile are acceptable dimensions for a trial. Avoid using session id, prompt
id, file path, full repo path, command text, or branch name as default metric
dimensions.

## Cardinality Policy

| Field | Logs | Traces | Metrics |
| --- | --- | --- | --- |
| `telemetry.team.id` | yes | yes | yes |
| `telemetry.user.email` | yes | yes | yes |
| `agent.tool` | yes | yes | yes |
| `model.name` | yes | yes | yes |
| `agent.session.id` | yes | yes | avoid |
| `agent.conversation.id` | yes | yes | avoid |
| `repo.remote` | yes | yes | avoid |
| `git.branch` | yes | yes | avoid by default |
| command strings | yes | selective | no |
| file paths | yes | selective | no |
| raw API bodies | selective | no | no |

## Capture Profiles

The capture profile is token metadata owned by `auth-api`. The auth response
includes `X-Telemetry-Capture-Profile`, Nginx forwards it as a trusted header,
and the Collector copies it into `agent.capture.profile`.

### normal

Default profile for the team trial. It captures logs, traces, metrics, tool
decisions, tool results, model/API events, and operational errors. Prompt and
tool content are disabled by default.

### max

Short-window forensic profile. It may include raw API request and response data
where the client supports it. It should have short retention and should require
explicit opt-in.

## Dashboard Dimensions

Starter dashboards should use these primary filters:

- `telemetry.team.id`
- `telemetry.user.email`
- `agent.tool`
- `model.name`
- `run.outcome`
- `agent.capture.profile`

## Initial Dashboard Set

1. Team overview:
   - events by user
   - events by `agent.tool`
   - active users per day
   - logs, traces, and metrics ingest volume
2. Codex overview:
   - conversations started
   - API request count
   - API request failures
   - API request duration
   - tool decisions
   - tool results
   - prompt count and prompt length
3. Claude Code overview:
   - sessions
   - token counters
   - cost counters
   - tool decisions
   - tool results
   - API errors
   - retry exhaustion
   - compaction events
4. Tool usage:
   - shell/tool calls by user
   - failed tool calls
   - slow tool calls
   - approval denials
5. Collector health:
   - exporter send failures
   - queue size
   - queue capacity
   - refused logs, spans, and metrics
   - memory limiter activity
6. Per-user drilldown:
   - filter by `telemetry.user.email`
   - filter by `telemetry.team.id`
   - filter by `agent.tool`

## Normalization Rule

Do not fully normalize agent schemas on day one. Native telemetry is valuable,
and premature normalization will hide useful tool-specific fields. Add trusted
identity attributes first, normalize `agent.tool`, then let dashboard needs
drive further schema work.
