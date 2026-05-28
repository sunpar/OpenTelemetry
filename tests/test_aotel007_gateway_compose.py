import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "compose/docker-compose.gateway.yml"


def _load_compose():
    return yaml.safe_load(COMPOSE_FILE.read_text())


def test_gateway_compose_config_validates():
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    config = yaml.safe_load(result.stdout)
    assert config["name"] == "agent-otel-gateway"
    assert set(config["services"]) == {"auth-api", "nginx", "otel-collector"}


def test_gateway_services_are_wired_to_repo_configs():
    compose = _load_compose()
    services = compose["services"]

    assert services["auth-api"]["build"] == {
        "context": "..",
        "dockerfile": "services/auth-api/Dockerfile",
    }
    assert services["auth-api"]["environment"]["AUTH_API_DB_PATH"] == "${AUTH_API_DB_PATH:-/data/auth-api.sqlite3}"
    assert "../:/workspace:ro" in services["auth-api"]["volumes"]
    assert "auth-api-data:/data" in services["auth-api"]["volumes"]

    assert services["nginx"]["image"].startswith("nginx:")
    assert "../infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" in services["nginx"]["volumes"]

    collector = services["otel-collector"]
    assert collector["image"].startswith("otel/opentelemetry-collector-contrib:")
    assert collector["command"] == ["--config=/etc/otelcol-contrib/collector.local.yaml"]
    assert "../infra/otel/collector.local.yaml:/etc/otelcol-contrib/collector.local.yaml:ro" in collector["volumes"]


def test_gateway_does_not_publish_internal_ingestion_ports():
    compose = _load_compose()

    assert "ports" not in compose["services"]["auth-api"]
    assert "ports" not in compose["services"]["otel-collector"]
    assert compose["services"]["nginx"]["ports"] == ["${GATEWAY_HOST:-127.0.0.1}:${GATEWAY_PORT:-8088}:8088"]

    for service in compose["services"].values():
        for port in service.get("ports", []) or []:
            rendered = str(port)
            assert "4317" not in rendered
            assert "4318" not in rendered


def test_gateway_collector_joins_private_signoz_network():
    compose = _load_compose()

    assert compose["services"]["otel-collector"]["networks"] == ["gateway", "signoz"]
    assert compose["services"]["nginx"]["networks"] == ["gateway"]
    assert compose["services"]["auth-api"]["networks"] == ["gateway"]
    assert compose["networks"]["gateway"]["name"] == "${GATEWAY_NETWORK:-agent-otel-gateway}"
    assert compose["networks"]["signoz"]["external"] is True
    assert compose["networks"]["signoz"]["name"] == "${SIGNOZ_NETWORK:-signoz-net}"


def test_makefile_wires_gateway_targets_and_otelctl_context():
    makefile = (ROOT / "Makefile").read_text()

    assert "$(DOCKER_COMPOSE) -f compose/docker-compose.gateway.yml up -d" in makefile
    assert "$(DOCKER_COMPOSE) -f compose/docker-compose.gateway.yml down" in makefile
    assert "$(DOCKER_COMPOSE) -f compose/docker-compose.gateway.yml logs -f" in makefile
    assert "$(DOCKER_COMPOSE) -f compose/docker-compose.gateway.yml exec -T auth-api" in makefile
    assert "$(DOCKER_COMPOSE) -f compose/docker-compose.gateway.yml config" in makefile
    assert "python /workspace/cli/otelctl/src/otelctl.py" in makefile
    assert "scripts/smoke-test-otel.py" in makefile
    assert "AOTEL_SMOKE_TOKEN" in makefile


def test_makefile_does_not_create_signoz_managed_network():
    makefile = (ROOT / "Makefile").read_text()

    assert "docker network create \"$(SIGNOZ_NETWORK)\"" not in makefile
    assert "-f $(SIGNOZ_COMPOSE_OVERRIDE) up -d --remove-orphans" in makefile
