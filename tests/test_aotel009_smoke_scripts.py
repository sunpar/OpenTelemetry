import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_script(relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_send_test_log_builds_signal_urls():
    sender = _load_script("scripts/send-test-log.py")

    assert sender.build_signal_url("http://localhost:8088", "/v1/logs") == "http://localhost:8088/v1/logs"
    assert sender.build_signal_url("http://localhost:8088/", "/v1/metrics") == "http://localhost:8088/v1/metrics"
    assert sender.build_signal_url("https://otel.example.com/base", "/v1/traces") == "https://otel.example.com/base/v1/traces"
    assert sender.build_signal_url("https://otel.example.com/v1/logs", "/v1/logs") == "https://otel.example.com/v1/logs"

    with pytest.raises(ValueError, match="already includes"):
        sender.build_signal_url("https://otel.example.com/v1/logs", "/v1/traces")


def test_send_test_log_payload_contains_resource_and_agent_fields():
    sender = _load_script("scripts/send-test-log.py")

    payload = sender.build_log_payload(
        message="hello smoke",
        service_name="codex",
        agent_tool="codex",
        run_mode="ci",
    )

    resource_attrs = {
        item["key"]: item["value"]["stringValue"]
        for item in payload["resourceLogs"][0]["resource"]["attributes"]
    }
    record = payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
    record_attrs = {
        item["key"]: item["value"]["stringValue"]
        for item in record["attributes"]
    }

    assert resource_attrs["service.name"] == "codex"
    assert resource_attrs["agent.tool"] == "codex"
    assert record_attrs["run.mode"] == "ci"
    assert record["body"]["stringValue"] == "hello smoke"
    assert record["severityText"] == "INFO"


def test_send_test_log_payloads_cover_all_valid_signals():
    sender = _load_script("scripts/send-test-log.py")

    trace_payload = sender.build_trace_payload(
        service_name="aotel-smoke",
        agent_tool="custom",
        run_mode="ci",
    )
    metric_payload = sender.build_metric_payload(
        service_name="aotel-smoke",
        agent_tool="custom",
        run_mode="ci",
    )

    span = trace_payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    metric = metric_payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]

    assert span["traceId"] == "00000000000000000000000000000001"
    assert span["spanId"] == "0000000000000001"
    assert metric["name"] == "agent_otel_smoke_metric"
    assert metric["gauge"]["dataPoints"][0]["asDouble"] == 1.0


def test_smoke_defaults_cover_auth_paths_and_direct_ports():
    smoke = _load_script("scripts/smoke-test-otel.py")

    args = smoke.build_parser().parse_args(["--endpoint", "http://localhost:8088"])

    assert args.signal_path == ["/v1/logs", "/v1/traces", "/v1/metrics"]
    assert args.direct_port is None
    assert smoke.default_direct_ports("http://localhost:8088") == ["127.0.0.1:4317", "127.0.0.1:4318"]
    assert smoke.default_direct_ports("http://10.0.0.5:8088") == [
        "10.0.0.5:4317",
        "10.0.0.5:4318",
        "127.0.0.1:4317",
        "127.0.0.1:4318",
    ]
    assert args.invalid_token == "invalid-token"


def test_smoke_token_sources_avoid_command_line_secrets(tmp_path, monkeypatch):
    smoke = _load_script("scripts/smoke-test-otel.py")

    monkeypatch.setenv("AOTEL_SMOKE_TOKEN", "TOKEN_FROM_ENV")
    args = smoke.build_parser().parse_args(["--endpoint", "http://localhost:8088"])
    assert smoke.read_token(args) == "TOKEN_FROM_ENV"

    token_file = tmp_path / "token"
    token_file.write_text("TOKEN_FROM_FILE\n")
    args = smoke.build_parser().parse_args(
        ["--endpoint", "http://localhost:8088", "--token-file", str(token_file)]
    )
    assert smoke.read_token(args) == "TOKEN_FROM_FILE"

    with pytest.raises(ValueError, match="exactly one token source"):
        args = smoke.build_parser().parse_args(
            [
                "--endpoint",
                "http://localhost:8088",
                "--token",
                "TOKEN_FROM_ARG",
                "--token-file",
                str(token_file),
            ]
        )
        smoke.read_token(args)


def test_smoke_script_rejects_real_token_literals_in_repo():
    checked_paths = [
        "scripts/smoke-test-otel.py",
        "scripts/send-test-log.py",
        "docs/operating.md",
        "docs/troubleshooting.md",
        "docs/agent-output/AOTEL-009.md",
    ]
    real_token = re.compile(r"aotel_live_tok_[0-9A-HJKMNPQRSTVWXYZ]{26}_[A-Za-z0-9_-]+")
    for relative_path in checked_paths:
        text = (ROOT / relative_path).read_text()
        assert real_token.search(text) is None


def test_live_compose_smoke_script_is_opt_in():
    if os.environ.get("AOTEL_RUN_COMPOSE_SMOKE") != "1":
        pytest.skip("set AOTEL_RUN_COMPOSE_SMOKE=1 and AOTEL_SMOKE_TOKEN to run live gateway smoke")

    token = os.environ["AOTEL_SMOKE_TOKEN"]
    endpoint = os.environ.get("AOTEL_SMOKE_ENDPOINT", "http://localhost:8088")
    result = subprocess.run(
        [
            "python3",
            "scripts/smoke-test-otel.py",
            "--endpoint",
            endpoint,
        ],
        cwd=ROOT,
        env={**os.environ, "AOTEL_SMOKE_TOKEN": token},
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
