#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from urllib import error, request
from urllib.parse import urlsplit, urlunsplit


ALLOWED_SIGNAL_PATHS = {"/v1/logs", "/v1/traces", "/v1/metrics"}


def build_signal_url(endpoint: str, signal_path: str) -> str:
    if signal_path not in ALLOWED_SIGNAL_PATHS:
        raise ValueError(f"unsupported OTLP signal path: {signal_path}")

    parts = urlsplit(endpoint.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("endpoint must be an absolute http(s) URL")

    base_path = parts.path.rstrip("/")
    if base_path in ALLOWED_SIGNAL_PATHS:
        if base_path != signal_path:
            raise ValueError(f"endpoint already includes {base_path}; cannot append {signal_path}")
        return urlunsplit(parts._replace(path=base_path))

    path = f"{base_path}{signal_path}" if base_path else signal_path
    return urlunsplit(parts._replace(path=path))


def _string_attr(key: str, value: str) -> dict:
    return {"key": key, "value": {"stringValue": value}}


def build_log_payload(
    *,
    message: str,
    service_name: str,
    agent_tool: str,
    run_mode: str,
) -> dict:
    now = str(time.time_ns())
    return {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        _string_attr("service.name", service_name),
                        _string_attr("agent.tool", agent_tool),
                        _string_attr("service.namespace", "agent-otel"),
                    ],
                },
                "scopeLogs": [
                    {
                        "scope": {"name": "agent-otel-trial.smoke", "version": "0.1.0"},
                        "logRecords": [
                            {
                                "timeUnixNano": now,
                                "observedTimeUnixNano": now,
                                "severityText": "INFO",
                                "severityNumber": 9,
                                "body": {"stringValue": message},
                                "attributes": [
                                    _string_attr("run.mode", run_mode),
                                    _string_attr("run.outcome", "success"),
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def build_trace_payload(
    *,
    service_name: str,
    agent_tool: str,
    run_mode: str,
) -> dict:
    now = time.time_ns()
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _string_attr("service.name", service_name),
                        _string_attr("agent.tool", agent_tool),
                        _string_attr("service.namespace", "agent-otel"),
                    ],
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "agent-otel-trial.smoke", "version": "0.1.0"},
                        "spans": [
                            {
                                "traceId": "00000000000000000000000000000001",
                                "spanId": "0000000000000001",
                                "name": "agent-otel smoke span",
                                "kind": 1,
                                "startTimeUnixNano": str(now),
                                "endTimeUnixNano": str(now + 1_000_000),
                                "attributes": [
                                    _string_attr("run.mode", run_mode),
                                    _string_attr("run.outcome", "success"),
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def build_metric_payload(
    *,
    service_name: str,
    agent_tool: str,
    run_mode: str,
) -> dict:
    now = str(time.time_ns())
    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        _string_attr("service.name", service_name),
                        _string_attr("agent.tool", agent_tool),
                        _string_attr("service.namespace", "agent-otel"),
                    ],
                },
                "scopeMetrics": [
                    {
                        "scope": {"name": "agent-otel-trial.smoke", "version": "0.1.0"},
                        "metrics": [
                            {
                                "name": "agent_otel_smoke_metric",
                                "description": "Agent OpenTelemetry smoke test metric",
                                "unit": "1",
                                "gauge": {
                                    "dataPoints": [
                                        {
                                            "timeUnixNano": now,
                                            "asDouble": 1.0,
                                            "attributes": [
                                                _string_attr("run.mode", run_mode),
                                                _string_attr("run.outcome", "success"),
                                            ],
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }


def post_json(url: str, payload: dict, headers: dict[str, str], timeout: float) -> tuple[int, str]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        **headers,
    }
    req = request.Request(url, data=body, headers=request_headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def send_log(
    *,
    endpoint: str,
    token: str,
    message: str,
    service_name: str = "aotel-smoke",
    agent_tool: str = "custom",
    run_mode: str = "ci",
    timeout: float = 5.0,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    url = build_signal_url(endpoint, "/v1/logs")
    payload = build_log_payload(
        message=message,
        service_name=service_name,
        agent_tool=agent_tool,
        run_mode=run_mode,
    )
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    status, body = post_json(url, payload, headers, timeout)
    return status, body, url


def send_signal(
    *,
    endpoint: str,
    token: str,
    signal_path: str,
    timeout: float = 5.0,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    builders = {
        "/v1/logs": lambda: build_log_payload(
            message="agent-otel smoke test log",
            service_name="aotel-smoke",
            agent_tool="custom",
            run_mode="ci",
        ),
        "/v1/traces": lambda: build_trace_payload(
            service_name="aotel-smoke",
            agent_tool="custom",
            run_mode="ci",
        ),
        "/v1/metrics": lambda: build_metric_payload(
            service_name="aotel-smoke",
            agent_tool="custom",
            run_mode="ci",
        ),
    }
    if signal_path not in builders:
        raise ValueError(f"unsupported OTLP signal path: {signal_path}")

    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    url = build_signal_url(endpoint, signal_path)
    status, body = post_json(url, builders[signal_path](), headers, timeout)
    return status, body, url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send one OTLP/HTTP JSON test log through the gateway.")
    parser.add_argument("--endpoint", required=True, help="Gateway base URL, for example http://localhost:8088")
    parser.add_argument("--token", required=True, help="Bearer token to use for Authorization")
    parser.add_argument("--message", default="agent-otel smoke test log")
    parser.add_argument("--service-name", default="aotel-smoke")
    parser.add_argument("--agent-tool", default="custom")
    parser.add_argument("--run-mode", default="ci")
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        status, body, url = send_log(
            endpoint=args.endpoint,
            token=args.token,
            message=args.message,
            service_name=args.service_name,
            agent_tool=args.agent_tool,
            run_mode=args.run_mode,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"failed to send test log: {exc}", file=sys.stderr)
        return 1

    if not 200 <= status < 300:
        print(f"test log rejected by {url}: status={status} body={body}", file=sys.stderr)
        return 1

    print(f"sent test log to {url}: status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
