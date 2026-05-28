#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import socket
import sys
from pathlib import Path
from urllib import error, request
from urllib.parse import urlsplit


DEFAULT_SIGNAL_PATHS = ["/v1/logs", "/v1/traces", "/v1/metrics"]
DEFAULT_DIRECT_PORTS = ["127.0.0.1:4318", "127.0.0.1:4317"]


def _load_sender():
    sender_path = Path(__file__).with_name("send-test-log.py")
    spec = importlib.util.spec_from_file_location("send_test_log", sender_path)
    if spec is None:
        raise RuntimeError(f"cannot load {sender_path}")
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load {sender_path}")
    spec.loader.exec_module(module)
    return module


SEND_TEST_LOG = _load_sender()


def post_empty_json(url: str, token: str, timeout: float, extra_headers: dict[str, str] | None = None) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = request.Request(url, data=b"{}", headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status
    except error.HTTPError as exc:
        return exc.code


def parse_host_port(value: str) -> tuple[str, int]:
    if "://" in value:
        parts = urlsplit(value)
        if not parts.hostname or not parts.port:
            raise ValueError(f"direct port must include host and port: {value}")
        return parts.hostname, parts.port

    host, sep, port_text = value.rpartition(":")
    if not sep or not host or not port_text:
        raise ValueError(f"direct port must look like host:port: {value}")
    return host, int(port_text)


def assert_port_closed(host: str, port: int, timeout: float) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except OSError:
        return
    finally:
        sock.close()
    raise RuntimeError(f"direct ingestion port is reachable on {host}:{port}")


def check_invalid_tokens(endpoint: str, invalid_token: str, paths: list[str], timeout: float) -> list[str]:
    failures: list[str] = []
    for path in paths:
        url = SEND_TEST_LOG.build_signal_url(endpoint, path)
        status = post_empty_json(url, invalid_token, timeout)
        if status != 401:
            failures.append(f"{path} expected 401 for invalid token, got {status}")
        else:
            print(f"ok invalid token rejected on {path}")
    return failures


def check_valid_log(endpoint: str, token: str, timeout: float) -> list[str]:
    spoofed_headers = {
        "X-Telemetry-User": "spoofed@example.com",
        "X-Telemetry-Team": "spoofed-team",
        "X-Telemetry-User-Id": "usr_spoofed",
        "X-Telemetry-Token-Id": "tok_spoofed",
        "X-Telemetry-Capture-Profile": "max",
        "X-Forwarded-For": "203.0.113.250",
    }
    status, body, url = SEND_TEST_LOG.send_log(
        endpoint=endpoint,
        token=token,
        message="agent-otel smoke test log",
        timeout=timeout,
        extra_headers=spoofed_headers,
    )
    if 200 <= status < 300:
        print(f"ok valid token accepted on /v1/logs: status={status}")
        print("ok spoofed X-Telemetry-* headers were sent through ingress overwrite path")
        return []
    return [f"valid token rejected by {url}: status={status} body={body}"]


def check_direct_ports(values: list[str], timeout: float) -> list[str]:
    failures: list[str] = []
    for value in values:
        try:
            host, port = parse_host_port(value)
            assert_port_closed(host, port, timeout)
        except Exception as exc:
            failures.append(str(exc))
        else:
            print(f"ok direct ingestion port unavailable on {value}")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local gateway smoke and security checks.")
    parser.add_argument("--endpoint", required=True, help="Gateway base URL, for example http://localhost:8088")
    parser.add_argument("--token", required=True, help="Valid bearer token issued by otelctl")
    parser.add_argument("--invalid-token", default="invalid-token")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--signal-path", action="append", default=list(DEFAULT_SIGNAL_PATHS))
    parser.add_argument("--direct-port", action="append", default=list(DEFAULT_DIRECT_PORTS))
    parser.add_argument("--skip-direct-port-check", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    failures: list[str] = []
    failures.extend(check_invalid_tokens(args.endpoint, args.invalid_token, args.signal_path, args.timeout))
    failures.extend(check_valid_log(args.endpoint, args.token, args.timeout))
    if not args.skip_direct_port_check:
        failures.extend(check_direct_ports(args.direct_port, args.timeout))

    if failures:
        print("smoke checks failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("smoke checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return run(args)
    except Exception as exc:
        print(f"smoke check error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
