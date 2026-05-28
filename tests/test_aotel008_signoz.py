import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "compose/docker-compose.signoz.yml"
OVERRIDE_FILE = ROOT / "compose/docker-compose.signoz.override.yml"
COMPOSE_CHECK_SCRIPT = ROOT / "scripts/check-signoz-compose-config.sh"
SIGNOZ_README = ROOT / "infra/signoz/README.md"
UPSTREAM_REVISION = "a8f5bdf2562c35c2896a5a287552e124fa2c0037"


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

    assert compose["networks"]["signoz-net"]["name"] == "signoz-net"
    assert compose["x-agent-otel-signoz"]["strategy"] == "official-compose-wrapper"
    assert "https://github.com/SigNoz/signoz.git" in compose["x-agent-otel-signoz"]["upstream"]
    assert compose["x-agent-otel-signoz"]["upstream_revision"] == UPSTREAM_REVISION
    assert compose["x-agent-otel-signoz"]["safe_override"] == "compose/docker-compose.signoz.override.yml"


def test_signoz_compose_does_not_publish_otlp_ingestion_ports():
    compose = yaml.safe_load(COMPOSE_FILE.read_text())

    for service in compose.get("services", {}).values():
        for port in service.get("ports", []) or []:
            rendered = str(port)
            assert "4317" not in rendered
            assert "4318" not in rendered


def test_signoz_override_binds_ui_and_removes_host_ingestion_ports():
    override = OVERRIDE_FILE.read_text()

    assert '"127.0.0.1:8080:8080"' in override
    assert "ports: !override []" in override
    assert "name: signoz-net" in override
    assert "${SIGNOZ_NETWORK" not in override


def test_signoz_override_merges_to_safe_host_bindings(tmp_path):
    upstream = tmp_path / "upstream-signoz.yml"
    upstream.write_text(
        "\n".join(
            [
                "name: upstream-signoz",
                "services:",
                "  signoz:",
                "    image: busybox",
                "    networks:",
                "      - signoz-net",
                "    ports:",
                '      - "8080:8080"',
                "  otel-collector:",
                "    image: busybox",
                "    networks:",
                "      - signoz-net",
                "    ports:",
                '      - "4317:4317"',
                '      - "4318:4318"',
                "networks:",
                "  signoz-net:",
                "    name: signoz-net",
                "",
            ]
        )
    )

    result = subprocess.run(
        ["docker", "compose", "-f", str(upstream), "-f", str(OVERRIDE_FILE), "config"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    config = yaml.safe_load(result.stdout)
    assert config["services"]["signoz"]["ports"] == [
        {
            "mode": "ingress",
            "host_ip": "127.0.0.1",
            "target": 8080,
            "published": "8080",
            "protocol": "tcp",
        }
    ]
    assert "ports" not in config["services"]["otel-collector"]
    assert "signoz-net" in config["services"]["otel-collector"]["networks"]


def test_signoz_compose_check_script_validates_override_stack(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGNOZ_VENDOR_DIR", str(tmp_path / "missing-signoz-vendor"))

    result = subprocess.run(
        ["bash", str(COMPOSE_CHECK_SCRIPT)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr


def test_signoz_readme_documents_bootstrap_and_private_ingestion():
    readme = SIGNOZ_README.read_text()

    for expected in [
        "git clone https://github.com/SigNoz/signoz.git .vendor/signoz",
        f"git -C .vendor/signoz checkout {UPSTREAM_REVISION}",
        "-f compose/docker-compose.signoz.override.yml",
        "http://localhost:8080",
        "Do not expose SigNoz OTLP ports",
        "compose/docker-compose.signoz.yml",
        "signoz-net",
        "retention",
    ]:
        assert expected in readme
