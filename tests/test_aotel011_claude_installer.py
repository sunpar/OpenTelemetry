import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMAL_TEMPLATE = ROOT / "templates/claude.env"
MAX_TEMPLATE = ROOT / "templates/claude.max-capture.env"
INSTALLER = ROOT / "scripts/install-claude-otel.sh"


def _run_installer(tmp_path, *extra_args, token="aotel_live_tok_abc_secret"):
    output = tmp_path / "claude.otel.env"
    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088/",
            "--token",
            token,
            "--output",
            str(output),
            *extra_args,
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result, output


def _source_env(path: Path):
    result = subprocess.run(
        ["bash", "-c", f"set -a; source {path}; env"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0, result.stderr
    env = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    return env


def test_claude_templates_are_shell_parseable():
    for template in [NORMAL_TEMPLATE, MAX_TEMPLATE]:
        result = subprocess.run(["bash", "-n", str(template)], check=False, text=True)
        assert result.returncode == 0


def test_installer_normal_profile_writes_safe_defaults(tmp_path):
    result, output = _run_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert "aotel_live_tok_abc_secret" not in result.stdout

    text = output.read_text()
    assert "CLAUDE_CODE_ENABLE_TELEMETRY=1" in text
    assert "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1" in text
    assert "OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf" in text
    assert "OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8088" in text
    assert "Authorization=Bearer" in text
    assert "OTEL_METRICS_INCLUDE_SESSION_ID=false" in text

    for forbidden in [
        "OTEL_LOG_USER_PROMPTS",
        "OTEL_LOG_TOOL_DETAILS",
        "OTEL_LOG_TOOL_CONTENT",
        "OTEL_LOG_RAW_API_BODIES",
    ]:
        assert f"unset {forbidden}" in text

    env = _source_env(output)
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://localhost:8088"
    assert env["OTEL_EXPORTER_OTLP_HEADERS"] == "Authorization=Bearer aotel_live_tok_abc_secret"
    for cleared in [
        "OTEL_LOG_USER_PROMPTS",
        "OTEL_LOG_TOOL_DETAILS",
        "OTEL_LOG_TOOL_CONTENT",
        "OTEL_LOG_RAW_API_BODIES",
    ]:
        assert cleared not in env


def test_installer_max_profile_refuses_without_trusted_token_metadata(tmp_path):
    result, output = _run_installer(
        tmp_path,
        "--profile",
        "max",
        "--token-capture-profile",
        "max",
    )

    assert result.returncode == 2
    assert not output.exists()
    assert "trusted token metadata" in result.stderr


def test_installer_escapes_opaque_secret_values(tmp_path):
    token = 'tok&sec $HOME `touch should-not-run` "quoted" \\ slash'
    result, output = _run_installer(
        tmp_path,
        token=token,
    )

    assert result.returncode == 0, result.stderr
    assert token not in result.stdout
    text = output.read_text()
    assert "{{TOKEN}}" not in text
    assert "tok{{TOKEN}}sec" not in text

    env = _source_env(output)
    assert env["OTEL_EXPORTER_OTLP_HEADERS"] == f"Authorization=Bearer {token}"


def test_installer_handles_token_equals_form_without_leaking_secret(tmp_path):
    output = tmp_path / "claude.otel.env"
    secret = "secret-value"
    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088/",
            f"--token={secret}",
            "--output",
            str(output),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert secret not in result.stdout
    assert secret not in result.stderr
    env = _source_env(output)
    assert env["OTEL_EXPORTER_OTLP_HEADERS"] == f"Authorization=Bearer {secret}"


def test_installer_does_not_modify_shell_startup_files(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    zshrc = home / ".zshrc"
    bashrc = home / ".bashrc"
    zshrc.write_text("export KEEP_ME=1\n")
    bashrc.write_text("export KEEP_ME_TOO=1\n")

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088",
            "--token",
            "tok",
            "--output",
            str(tmp_path / "claude.env"),
        ],
        check=False,
        env={**os.environ, "HOME": str(home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert zshrc.read_text() == "export KEEP_ME=1\n"
    assert bashrc.read_text() == "export KEEP_ME_TOO=1\n"


def test_claude_installer_script_is_parseable_shell():
    result = subprocess.run(["bash", "-n", str(INSTALLER)], check=False, text=True)
    assert result.returncode == 0


def test_make_install_claude_invokes_installer(tmp_path):
    output = tmp_path / "make-claude.env"
    result = subprocess.run(
        [
            "make",
            "install-claude",
            "ENDPOINT=http://localhost:8088/",
            "TOKEN=tok",
            f"OUTPUT={output}",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()
    env = _source_env(output)
    assert env["OTEL_EXPORTER_OTLP_HEADERS"] == "Authorization=Bearer tok"
