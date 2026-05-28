import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = ROOT / "infra/nginx/nginx.conf"


def _location_block(config: str, location: str) -> str:
    pattern = re.compile(rf"location\s+{re.escape(location)}\s*\{{(?P<body>.*?)\n\s*\}}", re.S)
    match = pattern.search(config)
    assert match is not None, f"missing location {location}"
    return match.group("body")


def _regex_location_block(config: str, location_regex: str) -> str:
    pattern = re.compile(rf"location\s+~\s+{location_regex}\s*\{{(?P<body>.*?)\n\s*\}}", re.S)
    match = pattern.search(config)
    assert match is not None, f"missing regex location {location_regex}"
    return match.group("body")


def test_nginx_allows_only_standard_otlp_http_paths():
    config = NGINX_CONF.read_text()
    otlp_block = _regex_location_block(config, r"\^/v1/\(logs\|traces\|metrics\)\$")

    assert "auth_request /_auth;" in otlp_block
    assert "proxy_pass http://otel_collector;" in otlp_block
    assert 'location = /healthz' in config
    assert "return 200" in _location_block(config, "= /healthz")
    assert "return 404;" in _location_block(config, "/")
    assert "proxy_pass http://otel_collector" not in config.replace(otlp_block, "")


def test_nginx_auth_subrequest_preserves_original_payload():
    config = NGINX_CONF.read_text()
    auth_block = _location_block(config, "= /_auth")

    assert "internal;" in auth_block
    assert "proxy_pass http://auth_api/auth/verify;" in auth_block
    assert "proxy_pass_request_body off;" in auth_block
    assert 'proxy_set_header Content-Length "";' in auth_block
    assert "proxy_set_header X-Original-Content-Length $http_content_length;" in auth_block
    assert "proxy_set_header Authorization $http_authorization;" in auth_block
    assert "proxy_set_header X-Original-URI $uri;" in auth_block
    assert "proxy_set_header X-Original-Method $request_method;" in auth_block
    assert "proxy_set_header X-Original-Content-Length $content_length;" in auth_block
    assert "proxy_set_header X-Telemetry-Source-Ip $remote_addr;" in auth_block


def test_nginx_overwrites_client_identity_headers_with_auth_response_values():
    config = NGINX_CONF.read_text()
    otlp_block = _regex_location_block(config, r"\^/v1/\(logs\|traces\|metrics\)\$")

    expected_sets = {
        "$telemetry_user": "$upstream_http_x_telemetry_user",
        "$telemetry_user_id": "$upstream_http_x_telemetry_user_id",
        "$telemetry_team": "$upstream_http_x_telemetry_team",
        "$telemetry_token_id": "$upstream_http_x_telemetry_token_id",
        "$telemetry_capture_profile": "$upstream_http_x_telemetry_capture_profile",
    }
    for variable, upstream_header in expected_sets.items():
        assert f"auth_request_set {variable} {upstream_header};" in otlp_block

    expected_headers = {
        "X-Telemetry-User": "$telemetry_user",
        "X-Telemetry-User-Id": "$telemetry_user_id",
        "X-Telemetry-Team": "$telemetry_team",
        "X-Telemetry-Token-Id": "$telemetry_token_id",
        "X-Telemetry-Capture-Profile": "$telemetry_capture_profile",
        "X-Telemetry-Source-Ip": "$remote_addr",
    }
    for header, value in expected_headers.items():
        assert f"proxy_set_header {header} {value};" in otlp_block


def test_nginx_collector_proxy_only_forwards_allowlisted_headers():
    config = NGINX_CONF.read_text()
    otlp_block = _regex_location_block(config, r"\^/v1/\(logs\|traces\|metrics\)\$")

    assert "proxy_pass_request_headers off;" in otlp_block
    assert "proxy_set_header Authorization" not in otlp_block

    expected_headers = {
        "Host": "$proxy_host",
        "Content-Type": "$content_type",
        "Content-Encoding": "$http_content_encoding",
        "Accept": "$http_accept",
        "User-Agent": "$http_user_agent",
    }
    for header, value in expected_headers.items():
        assert f"proxy_set_header {header} {value};" in otlp_block


def test_nginx_sets_otlp_body_limit_above_default():
    config = NGINX_CONF.read_text()
    otlp_block = _regex_location_block(config, r"\^/v1/\(logs\|traces\|metrics\)\$")

    assert "client_max_body_size 32m;" in otlp_block


def test_nginx_does_not_forward_client_supplied_x_forwarded_for_chain():
    config = NGINX_CONF.read_text()

    assert "$proxy_add_x_forwarded_for" not in config
    assert "set_real_ip_from 10.0.0.0/8;" not in config
    assert "set_real_ip_from 172.16.0.0/12;" not in config
    assert "set_real_ip_from 192.168.0.0/16;" not in config
    assert "real_ip_header X-Forwarded-For;" not in config
    assert "real_ip_recursive on;" not in config
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in config


def test_nginx_readme_documents_trust_boundary():
    readme = (ROOT / "infra/nginx/README.md").read_text()

    assert "auth_request" in readme
    assert "X-Telemetry-*" in readme
    assert "SigNoz" in readme
    assert "Collector" in readme
    assert "TLS" in readme
    assert "Real-IP handling is disabled by default" in readme
