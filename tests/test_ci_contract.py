import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
DEV_REQUIREMENTS = ROOT / "requirements-dev.txt"
DOC_CHECK = ROOT / "scripts/check-docs.py"


def test_ci_workflow_covers_core_validation_paths():
    workflow = yaml.safe_load(WORKFLOW.read_text())

    assert set(workflow["jobs"]) == {
        "python-tests",
        "static-validation",
        "compose-validation",
    }
    static_checkout = workflow["jobs"]["static-validation"]["steps"][0]
    assert static_checkout["uses"] == "actions/checkout@v4"
    assert static_checkout["with"]["fetch-depth"] == 0

    rendered = WORKFLOW.read_text()
    for expected in [
        "python -m pip install -r requirements-dev.txt",
        "python -m ruff check .",
        "python -m pytest -q",
        "python scripts/check-docs.py",
        "git diff --check",
        "fetch-depth: 0",
        "origin/${GITHUB_BASE_REF}...HEAD",
        "${{ github.event.before }}",
        "docker compose -f compose/docker-compose.gateway.yml config",
        "docker compose -f compose/docker-compose.signoz.yml config",
    ]:
        assert expected in rendered


def test_dev_requirements_install_local_packages_and_test_tools():
    requirements = DEV_REQUIREMENTS.read_text()

    for expected in [
        "-e services/auth-api",
        "-e cli/otelctl",
        "pytest",
        "ruff",
        "PyYAML",
        "httpx",
        "httpx2",
    ]:
        assert expected in requirements


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
