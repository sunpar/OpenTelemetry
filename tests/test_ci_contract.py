import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
DEV_REQUIREMENTS = ROOT / "requirements-dev.txt"
DOC_CHECK = ROOT / "scripts/check-docs.py"


def test_hosted_verification_is_explicit_and_bounded():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    triggers = workflow[True]  # PyYAML's YAML 1.1 loader treats "on" as true.
    assert set(triggers) == {"workflow_dispatch"}
    assert triggers["workflow_dispatch"]["inputs"]["suite"]["options"] == ["full", "smoke", "coverage"]
    job = workflow["jobs"]["verification"]
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] <= 10
    steps = job["steps"]
    assert steps[0]["with"]["fetch-depth"] == 0
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "make install-dev" in commands
    assert "make verify" in commands


def test_dev_requirements_install_local_packages_and_test_tools():
    requirements = DEV_REQUIREMENTS.read_text()

    for expected in [
        "-e packages/auth-core",
        "-e services/auth-api",
        "-e cli/otelctl",
        "pytest",
        "ruff",
        "PyYAML",
        "httpx",
        "httpx2",
    ]:
        assert expected in requirements


def test_makefile_exposes_local_validation_contract():
    result = subprocess.run(["make", "-n", "check"], cwd=ROOT, text=True, capture_output=True, check=True)
    for expected in [
        "-m ruff check .",
        "-m pytest -q",
        "scripts/check-docs.py",
    ]:
        assert expected in result.stdout
    assert "git diff" not in result.stdout
    assert "docker compose" not in result.stdout


def test_docs_checker_runs_static_validation():
    result = subprocess.run(
        [sys.executable, str(DOC_CHECK)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "ok markdown links" in result.stdout
    assert "ok onboarding TOML snippets" in result.stdout


def test_agent_context_docs_do_not_describe_pre_implementation_state():
    checked_docs = [
        ROOT / "docs/agent-context/test-commands.md",
        ROOT / "docs/agent-context/repo-map.md",
        ROOT / "docs/agent-context/architecture-index.md",
        ROOT / "docs/agent-plans/agent-otel-trial/test-baseline.md",
    ]
    stale_phrases = [
        "No runnable implementation exists yet",
        "documentation-only",
        "no source implementation",
        "No CI workflow exists",
        "No package manager or build files exist yet",
        "No Compose network topology exists yet",
        "No dashboard JSON exists yet",
    ]

    for path in checked_docs:
        text = path.read_text()
        for phrase in stale_phrases:
            assert phrase not in text
