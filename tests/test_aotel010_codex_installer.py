import os
import re
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/codex.config.toml"
INSTALLER = ROOT / "scripts/install-codex-otel.sh"
BACKUP = ROOT / "scripts/backup-codex-config.sh"


def _render_template(endpoint: str, token: str, log_user_prompt: str = "false") -> str:
    return (
        TEMPLATE.read_text()
        .replace("{{ENDPOINT}}", endpoint.rstrip("/"))
        .replace("{{TOKEN}}", token)
        .replace("{{LOG_USER_PROMPT}}", log_user_prompt)
    )


def test_codex_template_renders_to_parseable_content_minimal_toml():
    rendered = _render_template("https://otel.example.com", "aotel_live_tok_abc_secret")
    parsed = tomllib.loads(rendered)

    assert parsed["otel"]["environment"] == "team-trial"
    assert parsed["otel"]["log_user_prompt"] is False
    assert parsed["otel"]["exporter"]["otlp-http"]["endpoint"] == "https://otel.example.com/v1/logs"
    assert parsed["otel"]["metrics_exporter"]["otlp-http"]["endpoint"] == "https://otel.example.com/v1/metrics"
    assert parsed["otel"]["trace_exporter"]["otlp-http"]["endpoint"] == "https://otel.example.com/v1/traces"


def test_backup_helper_creates_timestamped_copy(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config = codex_home / "config.toml"
    config.write_text('model = "gpt-5"\n')
    config.chmod(0o644)

    result = subprocess.run(
        ["bash", str(BACKUP)],
        check=False,
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    backup_path = Path(result.stdout.strip())
    assert re.match(r"config\.toml\.bak\.\d{14}$", backup_path.name)
    assert backup_path.read_text() == 'model = "gpt-5"\n'
    assert backup_path.stat().st_mode & 0o777 == 0o600


def test_installer_preserves_unrelated_config_and_creates_backup(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config = codex_home / "config.toml"
    config.write_text('model = "gpt-5"\nprofile = "work"\n')

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088/",
            "--token",
            "aotel_live_tok_abc_secret",
        ],
        check=False,
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    updated = config.read_text()
    assert 'model = "gpt-5"' in updated
    assert 'profile = "work"' in updated
    assert "log_user_prompt = false" in updated
    assert "http://localhost:8088/v1/logs" in updated
    assert "aotel_live_tok_abc_secret" in updated
    assert len(list(codex_home.glob("config.toml.bak.*"))) == 1
    assert "aotel_live_tok_abc_secret" not in result.stdout

    cleaned = re.sub(
        r"(?ms)^# >>> agent-otel managed codex telemetry\n.*?^# <<< agent-otel managed codex telemetry\n?",
        "",
        updated,
    )
    assert cleaned.strip() == 'model = "gpt-5"\nprofile = "work"'
    tomllib.loads(re.search(r"(?ms)^# >>>.*?\n(.*?)^# <<<", updated).group(1))


def test_installer_replaces_only_existing_managed_block(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config = codex_home / "config.toml"

    env = {**os.environ, "CODEX_HOME": str(codex_home)}
    first = subprocess.run(
        ["bash", str(INSTALLER), "--endpoint", "http://one", "--token", "tok_one"],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert first.returncode == 0, first.stderr

    second = subprocess.run(
        ["bash", str(INSTALLER), "--endpoint", "http://two", "--token", "tok_two"],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert second.returncode == 0, second.stderr

    updated = config.read_text()
    assert updated.count("# >>> agent-otel managed codex telemetry") == 1
    assert "http://one/v1/logs" not in updated
    assert "tok_one" not in updated
    assert "http://two/v1/logs" in updated
    assert "tok_two" in updated


def test_installer_refuses_max_profile_without_trusted_capture_metadata(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088",
            "--token",
            "aotel_live_tok_abc_secret",
            "--profile",
            "max",
        ],
        check=False,
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert "trusted token metadata capture_profile=max" in result.stderr
    assert not (codex_home / "config.toml").exists()


def test_installer_accepts_max_profile_with_trusted_capture_metadata(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088",
            "--token",
            "aotel_live_tok_abc_secret",
            "--profile",
            "max",
            "--trusted-capture-profile",
            "max",
        ],
        check=False,
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    updated = (codex_home / "config.toml").read_text()
    assert "log_user_prompt = true" in updated


def test_installer_refuses_unmanaged_otel_table(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config = codex_home / "config.toml"
    original = '[otel]\nenvironment = "manual"\n'
    config.write_text(original)

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088",
            "--token",
            "aotel_live_tok_abc_secret",
        ],
        check=False,
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert "unmanaged [otel] table" in result.stderr
    assert config.read_text() == original
    assert len(list(codex_home.glob("config.toml.bak.*"))) == 1


def test_installer_refuses_unmatched_managed_markers(tmp_path):
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config = codex_home / "config.toml"
    original = (
        'model = "gpt-5"\n'
        "# >>> agent-otel managed codex telemetry\n"
        '[otel]\nenvironment = "team-trial"\n'
        'profile = "work"\n'
    )
    config.write_text(original)

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--endpoint",
            "http://localhost:8088",
            "--token",
            "aotel_live_tok_abc_secret",
        ],
        check=False,
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert "unmatched managed telemetry markers" in result.stderr
    assert config.read_text() == original
    assert len(list(codex_home.glob("config.toml.bak.*"))) == 1


def test_codex_installer_scripts_are_parseable_shell():
    for script in [INSTALLER, BACKUP]:
        result = subprocess.run(["bash", "-n", str(script)], check=False, text=True)
        assert result.returncode == 0
