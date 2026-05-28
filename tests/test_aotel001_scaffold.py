import importlib.util
import re
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_makefile_defines_documented_entry_points():
    makefile = (ROOT / "Makefile").read_text()

    for target in [
        "help",
        "signoz-up",
        "signoz-down",
        "up",
        "down",
        "logs",
        "user",
        "token",
        "smoke",
        "install-codex",
        "install-claude",
    ]:
        assert re.search(rf"^{re.escape(target)}\s*:", makefile, re.MULTILINE)

    assert "not implemented yet" in makefile.lower()


def test_env_example_contains_only_non_secret_defaults():
    env_text = (ROOT / ".env.example").read_text()

    for key in [
        "AOTEL_ENV=local",
        "AUTH_API_PORT=8000",
        "GATEWAY_PORT=8088",
        "OTEL_COLLECTOR_OTLP_HTTP_ENDPOINT=http://otel-collector:4318",
        "SIGNOZ_OTLP_GRPC_ENDPOINT=signoz-otel-collector:4317",
    ]:
        assert key in env_text

    forbidden = ["PASSWORD=", "SECRET=", "TOKEN=", "API_KEY=", "PRIVATE_KEY="]
    for marker in forbidden:
        assert marker not in env_text


def test_gitignore_covers_local_generated_artifacts():
    gitignore = (ROOT / ".gitignore").read_text()

    for pattern in [
        ".env",
        "!.env.example",
        "__pycache__/",
        ".pytest_cache/",
        ".venv/",
        "*.sqlite3",
        "*.sqlite3-wal",
        "*.sqlite3-shm",
        "*.sqlite3-journal",
        "services/auth-api/*.sqlite3-wal",
        ".vendor/",
        "signoz-data/",
    ]:
        assert pattern in gitignore


def test_python_package_metadata_is_valid():
    packages = {
        "services/auth-api/pyproject.toml": "agent-otel-auth-api",
        "cli/otelctl/pyproject.toml": "agent-otelctl",
    }

    for relative_path, expected_name in packages.items():
        data = tomllib.loads((ROOT / relative_path).read_text())
        assert data["project"]["name"] == expected_name
        assert data["project"]["requires-python"] == ">=3.11"
        assert data["build-system"]["build-backend"] == "setuptools.build_meta"

    cli_data = tomllib.loads((ROOT / "cli/otelctl/pyproject.toml").read_text())
    assert cli_data["project"]["scripts"]["otelctl"] == "otelctl:entrypoint"


def test_initial_source_packages_import_cleanly():
    package_versions = {
        "services/auth-api/src/auth_api/__init__.py": "0.1.0",
        "cli/otelctl/src/otelctl_auth/__init__.py": None,
    }
    for relative_init, expected_version in package_versions.items():
        module_name = relative_init.replace("/", "_").replace("-", "_").replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_init)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        if expected_version is not None:
            assert module.__version__ == expected_version


def test_make_help_runs_without_downstream_services():
    result = subprocess.run(
        ["make", "help"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert "Agent OpenTelemetry Trial" in result.stdout
    assert "make signoz-down" in result.stdout
    assert result.stderr == ""


def test_make_user_reports_required_variables_before_placeholder():
    result = subprocess.run(
        ["make", "user"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert "Missing required variable: EMAIL" in result.stdout
    assert "make user EMAIL=alice@example.com TEAM=quant-dev" in result.stdout
