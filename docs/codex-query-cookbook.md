# Codex Telemetry Query Cookbook

This document lists practical questions operators, engineering managers, and
platform owners will ask once many people send Codex telemetry into the shared
Agent OpenTelemetry stack.

The goal is not to make every possible query. The goal is to give a useful
starting set for token usage, prompt volume, tool usage, model/API behavior,
errors, adoption, and auth health while keeping sensitive content out of normal
dashboards.

## Query Surfaces

Use these stores for different questions:

| Surface | Best for | Primary tables |
| --- | --- | --- |
| SigNoz UI | Fast exploration, dashboards, filtering by user/team/tool | Logs, traces, metrics UI |
| ClickHouse SQL | Precise usage, grouped analytics, dashboard panels | `signoz_logs.*`, `signoz_traces.*`, `signoz_metrics.*` |
| Auth SQLite | Token inventory, token status, ingest audit | `users`, `tokens`, `ingest_audit` |

Local ClickHouse shell:

```sh
docker exec -it signoz-clickhouse clickhouse-client
```

Local SigNoz UI:

```text
http://localhost:8080
```

Current local Codex data should usually be filtered with:

```sql
resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
```

The `agent.tool` resource attribute is the intended cross-agent filter, but
local Codex rows may still need the `service.name` fallback until normalization
recognizes all Codex service names.

## Core Dimensions

Prefer these dimensions for dashboards and routine reports:

| Dimension | Source | Why it matters |
| --- | --- | --- |
| `telemetry.user.email` | Resource attribute | Per-user adoption, usage, support, quota review |
| `telemetry.team.id` | Resource attribute | Team-level adoption and chargeback |
| `telemetry.token.id` | Resource attribute | Token attribution and incident response |
| `agent.capture.profile` | Resource attribute | Separates normal capture from max/forensic capture |
| `service.name` | Resource attribute | Current reliable Codex filter |
| `event.name` | Log attribute | Codex event category |
| `tool_name` | Log/span attribute | Tool usage and failure rate |
| `conversation.id` | Log attribute | Conversation/session drilldown |
| `model` | Log/span attribute | Model mix where present |
| `codex.request.reasoning_effort` | Span attribute | Cost/performance analysis by reasoning effort |

Avoid default dashboard group-bys on prompt text, tool arguments, command
strings, full file paths, full repo paths, and session ids. Those fields are
valuable for drilldown, but they are sensitive and high cardinality.

## What People Will Want to Know

Start with these operator questions:

| Question | Primary signal | Practical answer |
| --- | --- | --- |
| Who is actively using Codex? | Logs | Daily active users by trusted email/team |
| How much token volume are we generating? | Traces | Sum request-level token attributes by user/team |
| Which users or teams are driving most usage? | Traces | Rank by total, input, output, cached, reasoning tokens |
| What is the model/API request mix? | Logs/traces | Count model request events; track missing model fields |
| How long do turns take? | Traces/metrics | p50/p95 `run_turn`, `session_task.turn`, TTFT/TTFM metrics |
| Which tools are used most? | Logs | Count `codex.tool_result` by `tool_name` |
| Which tools fail or run slowly? | Logs/traces | Failure counts and p95 durations by tool |
| How often are risky tools approved or denied? | Logs | Count `codex.tool_decision` by decision/tool/source |
| How much prompt activity is there? | Logs | Prompt event count and prompt length distribution |
| Are prompts or tool payloads being captured unexpectedly? | Logs | Audit prompt/content fields by capture profile |
| Are people using max capture? | Logs/traces/auth DB | Count by `agent.capture.profile` and token metadata |
| Are tokens revoked, stale, or abused? | Auth SQLite and logs | Token list, last seen, ingest failures, source IP |
| Is the gateway healthy? | Logs/metrics/auth audit | 401/403 rates, OTLP path volume, Collector errors |
| What data quality gaps block dashboards? | Logs/traces | Missing user/team/model/tool/capture fields |

## Token Usage

Codex currently exposes token data most reliably on trace numeric attributes.
There are two useful levels:

- Request-level token usage: `codex.usage.total_tokens`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
  `gen_ai.usage.cache_read.input_tokens`,
  `codex.usage.reasoning_output_tokens`.
- Turn-level token usage: `codex.turn.token_usage.*`.

Do not sum request-level and turn-level token fields together unless you have
verified they represent distinct accounting scopes for your client version.

### Token Usage by User

Use this for weekly usage review and rough chargeback:

```sql
SELECT
  resources_string['telemetry.user.email'] AS user,
  resources_string['telemetry.team.id'] AS team,
  sum(attributes_number['gen_ai.usage.input_tokens']) AS input_tokens,
  sum(attributes_number['gen_ai.usage.output_tokens']) AS output_tokens,
  sum(attributes_number['gen_ai.usage.cache_read.input_tokens']) AS cached_input_tokens,
  sum(attributes_number['codex.usage.reasoning_output_tokens']) AS reasoning_output_tokens,
  sum(attributes_number['codex.usage.total_tokens']) AS total_tokens,
  count() AS model_requests
FROM signoz_traces.distributed_signoz_index_v3
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND mapContains(attributes_number, 'codex.usage.total_tokens')
  AND timestamp >= now64(9) - INTERVAL 7 DAY
GROUP BY user, team
ORDER BY total_tokens DESC
LIMIT 100;
```

### Token Usage by Hour

Use this to understand daily peaks and whether capacity issues line up with
heavy model use:

```sql
SELECT
  toStartOfInterval(timestamp, INTERVAL 1 HOUR) AS hour,
  resources_string['telemetry.team.id'] AS team,
  sum(attributes_number['codex.usage.total_tokens']) AS total_tokens,
  count() AS model_requests
FROM signoz_traces.distributed_signoz_index_v3
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND mapContains(attributes_number, 'codex.usage.total_tokens')
  AND timestamp >= now64(9) - INTERVAL 7 DAY
GROUP BY hour, team
ORDER BY hour DESC, total_tokens DESC;
```

### Token Usage by Reasoning Effort

Use this to see whether high reasoning effort is materially changing token
consumption:

```sql
SELECT
  coalesce(nullIf(attributes_string['codex.request.reasoning_effort'], ''), 'unknown') AS reasoning_effort,
  count() AS model_requests,
  sum(attributes_number['codex.usage.total_tokens']) AS total_tokens,
  sum(attributes_number['codex.usage.reasoning_output_tokens']) AS reasoning_output_tokens,
  quantile(0.95)(duration_nano / 1000000) AS p95_ms
FROM signoz_traces.distributed_signoz_index_v3
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND mapContains(attributes_number, 'codex.usage.total_tokens')
  AND timestamp >= now64(9) - INTERVAL 7 DAY
GROUP BY reasoning_effort
ORDER BY total_tokens DESC;
```

### Turn-Level Token Distribution

Use this to find unusually expensive turns without mixing in lower-level model
request records:

```sql
SELECT
  resources_string['telemetry.user.email'] AS user,
  count() AS turns,
  quantile(0.50)(attributes_number['codex.turn.token_usage.total_tokens']) AS p50_tokens,
  quantile(0.95)(attributes_number['codex.turn.token_usage.total_tokens']) AS p95_tokens,
  max(attributes_number['codex.turn.token_usage.total_tokens']) AS max_tokens
FROM signoz_traces.distributed_signoz_index_v3
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND mapContains(attributes_number, 'codex.turn.token_usage.total_tokens')
  AND timestamp >= now64(9) - INTERVAL 7 DAY
GROUP BY user
ORDER BY p95_tokens DESC
LIMIT 100;
```

### Cost Estimates

Track tokens first. Cost requires a maintained model price schedule, and prices
change more often than the telemetry schema. A practical production pattern is:

1. Export token aggregates by model, user, team, and day.
2. Join them to a versioned price table outside SigNoz, or import a small
   price mapping table if you add a warehouse later.
3. Keep cached input, non-cached input, output, and reasoning output separate
   because they may have different pricing.

Current local data may not populate `model` on the trace rows that carry token
totals. Use the data-quality query below before promising model-level cost.

## Adoption and Activity

### Daily Active Users

Use this as the basic adoption panel:

```sql
SELECT
  toDate(fromUnixTimestamp64Nano(timestamp)) AS day,
  resources_string['telemetry.team.id'] AS team,
  uniqExact(resources_string['telemetry.user.email']) AS active_users,
  count() AS log_events
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 30 DAY)
GROUP BY day, team
ORDER BY day DESC, active_users DESC;
```

### Conversations Started

Use this as a better usage proxy than raw websocket event volume:

```sql
SELECT
  toDate(fromUnixTimestamp64Nano(timestamp)) AS day,
  resources_string['telemetry.user.email'] AS user,
  count() AS conversations
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.conversation_starts'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 30 DAY)
GROUP BY day, user
ORDER BY day DESC, conversations DESC;
```

### Recent User Activity Drilldown

Use this for support/debugging without selecting prompt text or tool payloads:

```sql
SELECT
  fromUnixTimestamp64Nano(timestamp) AS ts,
  resources_string['telemetry.user.email'] AS user,
  attributes_string['conversation.id'] AS conversation_id,
  attributes_string['event.name'] AS event_name,
  attributes_string['tool_name'] AS tool_name,
  attributes_string['model'] AS model,
  attributes_string['success'] AS success
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND resources_string['telemetry.user.email'] = 'alice@example.com'
ORDER BY timestamp DESC
LIMIT 200;
```

## Prompt Usage

Prompt fields are sensitive. For normal dashboards, count prompt events and
lengths without selecting raw prompt text.

### Prompt Volume and Length

Use this to understand activity and context size:

```sql
SELECT
  resources_string['telemetry.user.email'] AS user,
  resources_string['telemetry.team.id'] AS team,
  count() AS prompt_events,
  quantile(0.50)(toUInt64OrZero(attributes_string['prompt_length'])) AS p50_chars,
  quantile(0.95)(toUInt64OrZero(attributes_string['prompt_length'])) AS p95_chars,
  max(toUInt64OrZero(attributes_string['prompt_length'])) AS max_chars
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.user_prompt'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY user, team
ORDER BY prompt_events DESC;
```

### Prompt Capture Audit

Use this to verify whether prompt text is being captured, grouped by capture
profile:

```sql
SELECT
  resources_string['agent.capture.profile'] AS capture_profile,
  count() AS prompt_events,
  countIf(attributes_string['prompt'] != '') AS prompt_text_events,
  quantile(0.95)(toUInt64OrZero(attributes_string['prompt_length'])) AS p95_chars
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.user_prompt'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY capture_profile
ORDER BY prompt_text_events DESC;
```

Only inspect `attributes_string['prompt']` for an approved, scoped
investigation. Do not put raw prompt text on shared dashboards.

## Tool Usage

### Tool Calls by User and Tool

Use this to understand how people actually use Codex:

```sql
SELECT
  resources_string['telemetry.user.email'] AS user,
  attributes_string['tool_name'] AS tool,
  count() AS calls,
  countIf(attributes_string['success'] = 'false') AS failures,
  quantile(0.95)(toFloat64OrZero(attributes_string['duration_ms'])) AS p95_ms
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.tool_result'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY user, tool
ORDER BY calls DESC
LIMIT 100;
```

### Slow Tool Calls

Use this for developer-experience work. Slow tool calls often explain long turns
better than model latency alone:

```sql
SELECT
  attributes_string['tool_name'] AS tool,
  count() AS calls,
  quantile(0.50)(toFloat64OrZero(attributes_string['duration_ms'])) AS p50_ms,
  quantile(0.95)(toFloat64OrZero(attributes_string['duration_ms'])) AS p95_ms,
  max(toFloat64OrZero(attributes_string['duration_ms'])) AS max_ms
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.tool_result'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY tool
ORDER BY p95_ms DESC
LIMIT 50;
```

### Approval Decisions

Use this to audit risky operations and tune approval policy:

```sql
SELECT
  resources_string['telemetry.user.email'] AS user,
  attributes_string['tool_name'] AS tool,
  attributes_string['decision'] AS decision,
  attributes_string['source'] AS source,
  count() AS events
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.tool_decision'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY user, tool, decision, source
ORDER BY events DESC;
```

### Tool Payload Capture Audit

Tool arguments and output can include commands, file paths, snippets, and
secrets accidentally printed by commands. Use this to make sure payload capture
is understood:

```sql
SELECT
  resources_string['agent.capture.profile'] AS capture_profile,
  attributes_string['tool_name'] AS tool,
  count() AS tool_results,
  countIf(attributes_string['arguments'] != '') AS argument_events,
  countIf(attributes_string['output'] != '') AS output_events
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] = 'codex.tool_result'
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY capture_profile, tool
ORDER BY output_events DESC, argument_events DESC;
```

## Model and API Behavior

### Model Request Counts

Use log events for model mix where token-bearing trace spans do not yet carry
the model name:

```sql
SELECT
  coalesce(nullIf(attributes_string['model'], ''), 'unknown') AS model,
  attributes_string['reasoning_effort'] AS reasoning_effort,
  count() AS events
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND attributes_string['event.name'] IN ('codex.turn_ttft', 'codex.api_request')
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY model, reasoning_effort
ORDER BY events DESC;
```

### Model/API Errors

Use this to find provider instability, websocket disconnects, and request
failures:

```sql
SELECT
  attributes_string['event.name'] AS event_name,
  coalesce(nullIf(attributes_string['provider_name'], ''), 'unknown') AS provider,
  coalesce(nullIf(attributes_string['endpoint'], ''), 'unknown') AS endpoint,
  attributes_string['error.message'] AS error_message,
  count() AS events
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND (attributes_string['success'] = 'false' OR attributes_string['error.message'] != '')
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY event_name, provider, endpoint, error_message
ORDER BY events DESC
LIMIT 100;
```

### Turn Latency

Use trace spans for end-to-end turn latency:

```sql
SELECT
  name,
  count() AS spans,
  quantile(0.50)(duration_nano / 1000000) AS p50_ms,
  quantile(0.95)(duration_nano / 1000000) AS p95_ms,
  max(duration_nano / 1000000) AS max_ms
FROM signoz_traces.distributed_signoz_index_v3
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND name IN ('run_turn', 'session_task.turn', 'responses_websocket.stream_request')
  AND timestamp >= now64(9) - INTERVAL 7 DAY
GROUP BY name
ORDER BY p95_ms DESC;
```

## Metrics Exploration

Use metrics for stable time-series dashboards. Start by discovering available
metric names:

```sql
SELECT
  metric_name,
  any(type) AS type,
  any(unit) AS unit,
  max(toDateTime(last_reported_unix_milli / 1000)) AS last_seen
FROM signoz_metrics.distributed_metadata
WHERE metric_name LIKE 'codex.%'
GROUP BY metric_name
ORDER BY metric_name;
```

High-value metric families to explore first:

| Metric family | Why it is useful |
| --- | --- |
| `codex.turn.token_usage.*` | Token distributions over time |
| `codex.turn.e2e_duration_ms.*` | End-to-end turn latency |
| `codex.turn.ttft.duration_ms.*` | Time to first token |
| `codex.turn.ttfm.duration_ms.*` | Time to first model response |
| `codex.tool.call.duration_ms.*` | Tool-call latency |
| `codex.api_request.duration_ms.*` | API request latency |
| `codex.websocket.*` | Streaming behavior and disconnects |
| `codex.mcp.tools.*` | MCP tool discovery/cache health |
| `codex.startup.*` | Startup and prewarm behavior |

Use SigNoz dashboard query builder for histograms where possible; raw
ClickHouse histogram bucket queries are more verbose and easier to get wrong.

## Auth and Token Operations

Telemetry payloads live in SigNoz ClickHouse. Token and auth audit metadata live
in the auth-api SQLite database.

List a user's tokens without exposing token secrets:

```sh
docker compose -f compose/docker-compose.gateway.yml exec -T auth-api \
  env PYTHONPATH=/workspace/packages/auth-core/src:/workspace/cli/otelctl/src \
  python /workspace/cli/otelctl/src/otelctl.py \
  --db-path /data/auth-api.sqlite3 \
  tokens list --email alice@example.com
```

Useful SQLite questions:

```sql
-- Audit outcomes by path.
SELECT path, status_code, count(*) AS requests
FROM ingest_audit
GROUP BY path, status_code
ORDER BY requests DESC;

-- Token last-seen inventory.
SELECT
  u.email,
  u.team_id,
  t.id AS token_id,
  t.name,
  t.capture_profile,
  t.expires_at,
  t.revoked_at,
  t.last_seen_at
FROM tokens t
JOIN users u ON u.id = t.user_id
ORDER BY t.last_seen_at DESC;

-- Failed auth attempts by source.
SELECT
  remote_addr,
  path,
  status_code,
  count(*) AS attempts,
  max(created_at) AS last_seen
FROM ingest_audit
WHERE status_code != 204
GROUP BY remote_addr, path, status_code
ORDER BY attempts DESC;
```

## Data Quality Checks

Run these before building or trusting new dashboards.

### Missing Trusted Attributes

```sql
SELECT
  countIf(resources_string['telemetry.user.email'] = '') AS missing_user,
  countIf(resources_string['telemetry.team.id'] = '') AS missing_team,
  countIf(resources_string['telemetry.token.id'] = '') AS missing_token,
  countIf(resources_string['agent.capture.profile'] = '') AS missing_capture_profile,
  count() AS rows
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY);
```

### Token Rows Missing Model

If this returns a high count, model-level cost dashboards will be incomplete:

```sql
SELECT
  count() AS token_rows,
  countIf(attributes_string['model'] = '') AS missing_model_rows
FROM signoz_traces.distributed_signoz_index_v3
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND mapContains(attributes_number, 'codex.usage.total_tokens')
  AND timestamp >= now64(9) - INTERVAL 7 DAY;
```

### Event Inventory

Use this when Codex changes its telemetry schema:

```sql
SELECT
  attributes_string['event.name'] AS event_name,
  count() AS rows,
  max(fromUnixTimestamp64Nano(timestamp)) AS last_seen
FROM signoz_logs.distributed_logs_v2
WHERE resources_string['service.name'] IN ('codex_cli_rs', 'codex-app-server', 'codex')
  AND timestamp >= toUnixTimestamp64Nano(now64(9) - INTERVAL 7 DAY)
GROUP BY event_name
ORDER BY rows DESC;
```

## Dashboard Recommendations

Build dashboards in this order:

1. Team usage overview: active users, conversations, logs/spans/metric points,
   token usage by team, and max-capture usage.
2. Cost and capacity: request-level tokens by user/team/hour, cached input
   tokens, reasoning output tokens, and p95 turn latency.
3. Tool usage: calls by tool, failures, slow calls, approval decisions, and
   payload-capture audit.
4. Prompt safety: prompt event count, prompt length distribution, prompt text
   capture audit, and capture profile split.
5. Reliability: API/model errors, websocket disconnects, failed tool results,
   slow turns, and Collector/gateway health.
6. Token operations: active/revoked/expired token inventory, last seen, failed
   auth attempts, and unknown token attempts.
7. Data quality: missing trusted attributes, missing model on token rows,
   unknown service names, and new event names.

For shared dashboards, default to the last 7 days, filter by team/user/tool, and
avoid raw prompt or tool payload columns. Keep raw-content queries as
restricted, incident-response workflows.
