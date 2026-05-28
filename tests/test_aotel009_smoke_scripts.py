import importlib.util
import os
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


def test_smoke_defaults_cover_auth_paths_and_direct_ports():
    smoke = _load_script("scripts/smoke-test-otel.py")

    args = smoke.build_parser().parse_args(["--endpoint", "http://localhost:8088", "--token", "TOKEN"])

    assert args.signal_path == ["/v1/logs", "/v1/traces", "/v1/metrics"]
    assert args.direct_port == ["127.0.0.1:4318", "127.0.0.1:4317"]
    assert args.invalid_token == "invalid-token"


def test_smoke_script_rejects_real_token_literals_in_repo():
    for relative_path in ["scripts/smoke-test-otel.py", "scripts/send-test-log.py"]:
        text = (ROOT / relative_path).read_text()
        assert "aotel_live_tok_" not in text
        assert "Bearer <" not in text


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
            "--token",
            token,
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
