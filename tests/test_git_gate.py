import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_socket import SocketConnectBlockedError


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git-gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("git_gate", SCRIPT)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), "-c", "core.hooksPath=/dev/null", *args], text=True
    ).strip()


def commit(root):
    git(root, "add", ".")
    git(root, "-c", "user.name=Gate Test", "-c", "user.email=gate@example.com", "commit", "-qm", "Fixture")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    for name in ["requirements-dev.txt", "requirements-dev.lock", ".gitignore"]:
        shutil.copy2(ROOT / name, root / name)
    for name in ["packages", "services", "cli"]:
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    (root / "Makefile").write_text("check smoke-check:\n\t$(PYTHON) verify_fixture.py\n")
    (root / "verify_fixture.py").write_text(
        "import importlib.util, os\n"
        "from pathlib import Path\n"
        "import agent_otel_auth_core.tokens as tokens\n"
        "root = Path(__file__).resolve().parent\n"
        "assert tokens.__file__.startswith(str(root))\n"
        "assert importlib.util.find_spec('agent_otel_auth_core.working_only') is None\n"
        "assert os.environ.get('AOTEL_RUN_COMPOSE_SMOKE') is None\n"
        "assert os.environ.get('AOTEL_SMOKE_TOKEN') is None\n"
        "assert (root / 'value').read_text() == 'good'\n"
        "print('verified snapshot source')\n"
    )
    (root / "value").write_text("good")
    git(root, "init", "-q", "-b", "topic")
    sha = commit(root)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-q", str(remote))
    git(root, "remote", "add", "origin", str(remote))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "with Path(os.environ['GATE_GH_LOG']).open('a') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:3] == ['repo', 'view']:\n"
        "    print(json.dumps({'nameWithOwner':'owner/otel','isFork':False,'parent':None}))\n"
        "elif sys.argv[1:3] == ['pr', 'list']:\n"
        "    if os.environ.get('GATE_LOOKUP_ERROR') == '1':\n"
        "        print('PR lookup unavailable', file=sys.stderr)\n"
        "        sys.exit(5)\n"
        "    print(json.dumps([{'headRepository':{'name':'otel'},'headRepositoryOwner':{'login':'owner'}}]))\n"
        "elif sys.argv[1:3] == ['pr', 'create']:\n"
        "    print('created PR')\n"
        "else:\n"
        "    sys.exit(9)\n"
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GATE_GH_LOG", str(tmp_path / "gh.log"))
    return root, sha


def run_gate(root, *args, input=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=root, text=True,
        input=input, capture_output=True, timeout=90, check=False,
    )


def test_archive_uses_frozen_index_instead_of_working_tree(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "value").write_text("staged")
    git(tmp_path, "add", "value")
    tree = git(tmp_path, "write-tree")
    (tmp_path / "value").write_text("unstaged")
    with load_gate().snapshot(tmp_path, tree) as checked:
        assert (checked / "value").read_text() == "staged"
        assert not (checked / ".git").exists()
    assert not checked.exists()


def test_default_test_configuration_blocks_external_connections():
    with socket.socket() as connection:
        with pytest.warns(UserWarning, match="198.51.100.1"), pytest.raises(SocketConnectBlockedError):
            connection.connect(("198.51.100.1", 443))


def test_commit_gate_rejects_broken_staged_snapshot_with_good_worktree(repository):
    root, _ = repository
    (root / "value").write_text("broken")
    git(root, "add", "value")
    (root / "value").write_text("good")
    result = run_gate(root, "commit")
    assert result.returncode != 0
    assert "AssertionError" in result.stderr
    assert (root / "value").read_text() == "good"
    assert git(root, "show", ":value") == "broken"


def test_verified_commit_cannot_import_unstaged_source_or_inherit_skip_flags(repository, monkeypatch):
    root, sha = repository
    (root / "packages/auth-core/src/agent_otel_auth_core/working_only.py").write_text("SECRET = 1\n")
    monkeypatch.setenv("MAKEFLAGS", "n")
    monkeypatch.setenv("PYTHON", "/missing/python")
    monkeypatch.setenv("UV_PYTHON", "/missing/python")
    monkeypatch.setenv("AOTEL_RUN_COMPOSE_SMOKE", "1")
    monkeypatch.setenv("AOTEL_SMOKE_TOKEN", "never-send")
    result = run_gate(root, "check", sha)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verified snapshot source" in result.stdout


def test_push_checks_outgoing_sha_even_when_head_is_good(repository):
    root, _ = repository
    (root / "value").write_text("broken")
    outgoing = commit(root)
    (root / "value").write_text("good")
    commit(root)
    result = run_gate(
        root, "push", "origin", git(root, "remote", "get-url", "origin"),
        input=f"refs/heads/older {outgoing} refs/heads/topic {'0' * 40}\n",
    )
    assert result.returncode != 0
    assert "AssertionError" in result.stderr


def test_failed_pr_lookup_blocks_push(repository, monkeypatch):
    root, sha = repository
    monkeypatch.setenv("GATE_LOOKUP_ERROR", "1")
    result = run_gate(root, "push", "origin", git(root, "remote", "get-url", "origin"),
                      input=f"refs/heads/topic {sha} refs/heads/topic {'0' * 40}\n")
    assert result.returncode != 0
    assert "PR lookup unavailable" in result.stderr


def test_changed_dependencies_block_before_running_checks(repository):
    root, _ = repository
    with (root / "requirements-dev.txt").open("a") as f:
        f.write("missing-dependency==1\n")
    sha = commit(root)
    result = run_gate(root, "check", sha)
    assert result.returncode != 0
    assert "make lock" in result.stderr
    assert "verified snapshot source" not in result.stdout


def test_empty_dependency_cache_is_an_actionable_failure(repository, tmp_path, monkeypatch):
    root, sha = repository
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "empty-cache"))
    result = run_gate(root, "check", sha)
    assert result.returncode != 0
    assert "make install-dev" in result.stderr
    assert "verified snapshot source" not in result.stdout


def test_dependency_setup_can_refresh_an_existing_environment(repository):
    root, _ = repository
    gate = load_gate()
    gate.install(root, offline=True)
    gate.install(root, offline=True)
    result = subprocess.run([str(root / ".venv/bin/python"), "verify_fixture.py"],
                            cwd=root, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_failed_verification_prevents_push_and_pr_creation(repository):
    root, _ = repository
    (root / "value").write_text("broken")
    commit(root)
    result = run_gate(root, "pr", "--title", "Change fixture", "--body", "Verified locally")
    assert result.returncode != 0
    assert git(root, "ls-remote", "origin") == ""
    calls = Path(os.environ["GATE_GH_LOG"])
    assert not calls.exists() or all(json.loads(line)[:2] != ["pr", "create"] for line in calls.read_text().splitlines())


def test_pr_wrapper_pushes_verified_commit_and_assigns_author(repository):
    root, sha = repository
    (root / "value").write_text("unstaged")
    result = run_gate(root, "pr", "--title", "Change fixture", "--body", "Verified locally")
    assert result.returncode == 0, result.stdout + result.stderr
    assert git(root, "ls-remote", "origin", "refs/heads/topic").split()[0] == sha
    calls = [json.loads(line) for line in Path(os.environ["GATE_GH_LOG"]).read_text().splitlines()]
    created = next(call for call in calls if call[:2] == ["pr", "create"])
    assert created[created.index("--head") + 1] == "topic"
    assert created[created.index("--repo") + 1] == "owner/otel"
    assert created[created.index("--assignee") + 1] == "@me"


@pytest.mark.parametrize("args", [["--head", "other"], ["--repo=other/repo"], ["--web"], ["-dt", "title"]])
def test_pr_wrapper_rejects_options_that_escape_verification(tmp_path, args):
    git(tmp_path, "init", "-q")
    result = run_gate(tmp_path, "pr", *args)
    assert result.returncode != 0
    assert "Unsupported PR option" in result.stderr
