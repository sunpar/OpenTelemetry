import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "compose/docker-compose.signoz.yml"
SIGNOZ_README = ROOT / "infra/signoz/README.md"


def test_signoz_compose_config_validates():
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
    assert config["name"] == "agent-otel-signoz"


def test_signoz_compose_declares_private_gateway_network_contract():
    compose = yaml.safe_load(COMPOSE_FILE.read_text())

    assert compose["networks"]["signoz"]["name"] == "${SIGNOZ_NETWORK:-signoz-net}"
    assert compose["x-agent-otel-signoz"]["strategy"] == "official-compose-wrapper"
    assert "https://github.com/SigNoz/signoz.git" in compose["x-agent-otel-signoz"]["upstream"]


def test_signoz_compose_does_not_publish_otlp_ingestion_ports():
    compose = yaml.safe_load(COMPOSE_FILE.read_text())

    for service in compose.get("services", {}).values():
        for port in service.get("ports", []) or []:
            rendered = str(port)
            assert "4317" not in rendered
            assert "4318" not in rendered


def test_signoz_readme_documents_bootstrap_and_private_ingestion():
    readme = SIGNOZ_README.read_text()

    for expected in [
        "git clone -b main https://github.com/SigNoz/signoz.git .vendor/signoz",
        "docker compose -f .vendor/signoz/deploy/docker/docker-compose.yaml up -d --remove-orphans",
        "http://localhost:8080",
        "Do not expose SigNoz OTLP ports",
        "compose/docker-compose.signoz.yml",
        "retention",
    ]:
        assert expected in readme
