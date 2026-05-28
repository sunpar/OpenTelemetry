import subprocess
from pathlib import Path
from textwrap import dedent

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "compose/docker-compose.signoz.yml"
MAKEFILE = ROOT / "Makefile"
OVERRIDE_FILE = ROOT / "compose/docker-compose.signoz.override.yml"
COMPOSE_CHECK_SCRIPT = ROOT / "scripts/check-signoz-compose-config.sh"
SIGNOZ_README = ROOT / "infra/signoz/README.md"
UPSTREAM_REVISION = "a8f5bdf2562c35c2896a5a287552e124fa2c0037"
SIGNOZ_NETWORK_NAME = "signoz-net"
SIGNOZ_UI_BINDING = '"127.0.0.1:8080:8080"'
OTLP_INGESTION_PORTS = ("4317", "4318")
STATIC_COLLECTOR_CONFIG_ARG = "--config=/etc/otel-collector-config.yaml"
OPAMP_COLLECTOR_ARGS = ("--manager-config", "--copy-path")
UPSTREAM_OPAMP_COLLECTOR_COMMAND = (
    f"/signoz-otel-collector {STATIC_COLLECTOR_CONFIG_ARG} "
    f"{OPAMP_COLLECTOR_ARGS[0]}=/etc/manager-config.yaml "
    f"{OPAMP_COLLECTOR_ARGS[1]}=/var/tmp/collector-config.yaml"
)


def _compose_config(*compose_files: Path):
    command = ["docker", "compose"]
    for compose_file in compose_files:
        command.extend(["-f", str(compose_file)])
    command.append("config")

    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    return yaml.safe_load(result.stdout)


def _assert_static_collector_config_without_opamp(command_text: str):
    assert STATIC_COLLECTOR_CONFIG_ARG in command_text
    for opamp_arg in OPAMP_COLLECTOR_ARGS:
        assert opamp_arg not in command_text


def test_signoz_compose_config_validates():
    config = _compose_config(COMPOSE_FILE)
    assert config["name"] == "agent-otel-signoz"


def test_signoz_compose_declares_private_gateway_network_contract():
    compose = yaml.safe_load(COMPOSE_FILE.read_text())

    assert compose["networks"][SIGNOZ_NETWORK_NAME]["name"] == SIGNOZ_NETWORK_NAME
    assert compose["x-agent-otel-signoz"]["strategy"] == "official-compose-wrapper"
    assert "https://github.com/SigNoz/signoz.git" in compose["x-agent-otel-signoz"]["upstream"]
    assert compose["x-agent-otel-signoz"]["upstream_revision"] == UPSTREAM_REVISION
    assert compose["x-agent-otel-signoz"]["safe_override"] == "compose/docker-compose.signoz.override.yml"


def test_signoz_compose_does_not_publish_otlp_ingestion_ports():
    compose = yaml.safe_load(COMPOSE_FILE.read_text())

    for service in compose.get("services", {}).values():
        for port in service.get("ports", []) or []:
            rendered = str(port)
            for ingestion_port in OTLP_INGESTION_PORTS:
                assert ingestion_port not in rendered


def test_signoz_override_binds_ui_and_removes_host_ingestion_ports():
    override = OVERRIDE_FILE.read_text()

    assert SIGNOZ_UI_BINDING in override
    assert "ports: !override []" in override
    assert "command: !override" in override
    _assert_static_collector_config_without_opamp(override)
    assert f"name: {SIGNOZ_NETWORK_NAME}" in override
    assert "${SIGNOZ_NETWORK" not in override


def test_signoz_override_merges_to_safe_host_bindings(tmp_path):
    upstream = tmp_path / "upstream-signoz.yml"
    upstream.write_text(
        dedent(
            f"""\
            name: upstream-signoz
            services:
              signoz:
                image: busybox
                networks:
                  - {SIGNOZ_NETWORK_NAME}
                ports:
                  - "8080:8080"
              otel-collector:
                image: busybox
                command:
                  - -c
                  - |
                    /signoz-otel-collector migrate sync check &&
                    {UPSTREAM_OPAMP_COLLECTOR_COMMAND}
                networks:
                  - {SIGNOZ_NETWORK_NAME}
                ports:
                  - "4317:4317"
                  - "4318:4318"
            networks:
              {SIGNOZ_NETWORK_NAME}:
                name: {SIGNOZ_NETWORK_NAME}
            """
        )
    )

    config = _compose_config(upstream, OVERRIDE_FILE)
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
    assert SIGNOZ_NETWORK_NAME in config["services"]["otel-collector"]["networks"]
    collector_command = "\n".join(config["services"]["otel-collector"]["command"])
    _assert_static_collector_config_without_opamp(collector_command)


def test_signoz_makefile_startup_uses_pinned_upstream_revision():
    makefile = MAKEFILE.read_text()

    assert f"SIGNOZ_UPSTREAM_REVISION ?= {UPSTREAM_REVISION}" in makefile
    assert "git clone https://github.com/SigNoz/signoz.git" in makefile
    assert "git clone -b main" not in makefile
    fetch_command = (
        'git -C "$(SIGNOZ_VENDOR_DIR)" fetch --depth 1 origin '
        '"$(SIGNOZ_UPSTREAM_REVISION)"'
    )
    checkout_command = (
        'git -C "$(SIGNOZ_VENDOR_DIR)" checkout --detach '
        '"$(SIGNOZ_UPSTREAM_REVISION)"'
    )
    assert fetch_command in makefile
    assert checkout_command in makefile


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
