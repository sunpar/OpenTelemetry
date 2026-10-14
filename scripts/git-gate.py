#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit


PACKAGES = ("packages/auth-core", "services/auth-api", "cli/otelctl")
MANIFESTS = ("requirements-dev.txt", *(f"{path}/pyproject.toml" for path in PACKAGES))
LOCAL_DISTRIBUTIONS = ("agent-otel-auth-core", "agent-otel-auth-api", "agent-otelctl")


def environment():
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("GIT_", "UV_", "AOTEL_", "AUTH_API_", "COMPOSE_", "PYTHON", "PYTEST_"))
        and key not in {
            "MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "MAKELEVEL", "MAKEFILES", "VIRTUAL_ENV", "CONDA_PREFIX",
            "DOCKER_COMPOSE", "SIGNOZ_VENDOR_DIR", "SIGNOZ_COMPOSE_OVERRIDE",
        }
    }
    if "UV_CACHE_DIR" in os.environ:
        env["UV_CACHE_DIR"] = os.environ["UV_CACHE_DIR"]
    return env


def run(root, *args, **options):
    return subprocess.run(args, cwd=root, check=True, **options)


def git(root, *args, input=None, text=True):
    env = {key: value for key, value in os.environ.items()
           if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX"}}
    output = subprocess.check_output(
        ["git", "-C", str(root), *args], env=env, input=input, text=text
    )
    return output.strip() if text else output


def fingerprint(root):
    digest = hashlib.sha256()
    for name in sorted(MANIFESTS):
        digest.update(name.encode() + b"\0" + (root / name).read_bytes())
    return digest.hexdigest()


def lock(root):
    args = [
        "uv", "pip", "compile", "requirements-dev.txt", "--universal", "--python-version", "3.11",
        "--no-python-downloads", "--no-config", "--no-header", "--no-annotate",
        "--output-file", "requirements-dev.lock",
    ]
    for name in LOCAL_DISTRIBUTIONS:
        args.extend(["--no-emit-package", name])
    run(root, *args, env=environment())
    path = root / "requirements-dev.lock"
    path.write_text(f"# inputs-sha256: {fingerprint(root)}\n" + path.read_text())


def install(root, offline=False):
    path = root / "requirements-dev.lock"
    if not path.exists() or not path.read_text().startswith(f"# inputs-sha256: {fingerprint(root)}\n"):
        raise ValueError("Dependencies changed or lock missing. Run make lock, then make install-dev; stage the lock with its manifests.")
    common = ["--no-config", "--no-python-downloads", *(["--offline"] if offline else [])]
    env = environment()
    python = str(root / ".venv/bin/python")
    run(root, "uv", "venv", "--python", "3.11", "--clear", *common, ".venv", env=env)
    run(root, "uv", "pip", "sync", "--python", python, *common,
        "--only-binary", ":all:", "requirements-dev.lock", env=env)
    args = ["uv", "pip", "install", "--python", python, *common, "--no-deps", "--no-build-isolation"]
    for package in PACKAGES:
        args.extend(["-e", package])
    run(root, *args, env=env)
    run(root, "uv", "pip", "check", "--python", python, *common, env=env)
    return python


@contextmanager
def snapshot(root, selection):
    with TemporaryDirectory(prefix="otel-check-") as directory:
        archive = git(root, "archive", selection, text=False)
        run(root, "tar", "-xf", "-", "-C", directory, input=archive)
        yield Path(directory)


def verify(root, selection, suite="check"):
    if suite not in {"check", "smoke-check", "coverage"}:
        raise ValueError("Verification suite must be check, smoke-check or coverage")
    tree = git(root, "rev-parse", f"{selection}^{{tree}}")
    empty_tree = git(root, "hash-object", "-w", "-t", "tree", "--stdin", input="")
    git(root, "diff", "--check", empty_tree, tree)
    print(f"Checking {selection} ({suite})", flush=True)
    with snapshot(root, tree) as checked:
        python = install(checked, offline=True)
        run(checked, "make", suite, f"PYTHON={python}", env=environment())
        if suite == "coverage":
            shutil.copy2(checked / "coverage.xml", root / "coverage.xml")


def remote_repository(root, url):
    parsed = urlsplit(url)
    safe_url = parsed._replace(netloc=parsed.netloc.rsplit("@", 1)[-1], query="", fragment="").geturl()
    repository = json.loads(run(root, "gh", "repo", "view", safe_url, "--json", "nameWithOwner,isFork,parent",
                                text=True, capture_output=True).stdout)
    destination = repository["nameWithOwner"]
    parent = repository["parent"]
    target = f"{parent['owner']['login']}/{parent['name']}" if repository["isFork"] else destination
    return destination, target


def gate_push(root, url, input):
    updates = [line.split() for line in input.splitlines() if line.strip()]
    updates = [(sha, ref) for _, sha, ref, _ in updates
               if sha.strip("0") and ref.startswith("refs/heads/")]
    if not updates:
        return
    destination, target = remote_repository(root, url)
    tips = set()
    for sha, ref in updates:
        branch = ref.removeprefix("refs/heads/")
        for repo in dict.fromkeys((destination, target)):
            prs = json.loads(run(
                root, "gh", "pr", "list", "--repo", repo, "--state", "open", "--head", branch,
                "--json", "headRepository,headRepositoryOwner", text=True, capture_output=True,
            ).stdout)
            if any(f"{pr['headRepositoryOwner']['login']}/{pr['headRepository']['name']}".lower()
                   == destination.lower() for pr in prs):
                tips.add(sha)
        if branch == "main":
            tips.add(sha)
    for sha in sorted(tips):
        verify(root, sha)


def create_pr(root, args):
    values = {"--title", "-t", "--body", "-b", "--body-file", "-F", "--base", "-B",
              "--reviewer", "-r", "--label", "-l", "--milestone", "-m"}
    switches = {"--draft", "-d", "--fill", "-f", "--fill-first", "--fill-verbose", "--no-maintainer-edit"}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.split("=", 1)[0] in values:
            if "=" not in arg:
                index += 1
                if index == len(args):
                    raise ValueError(f"Missing value for PR option {arg}")
        elif arg not in switches:
            raise ValueError(f"Unsupported PR option {arg}; use title/body/base/reviewer/label/draft options without head or repo overrides.")
        index += 1
    branch = git(root, "symbolic-ref", "--short", "HEAD")
    sha = git(root, "rev-parse", "HEAD")
    url = git(root, "remote", "get-url", "--push", "origin")
    destination, repository = remote_repository(root, url)
    head = branch if destination == repository else f"{destination.split('/')[0]}:{branch}"
    verify(root, sha)
    run(root, "git", "push", "origin", f"{sha}:refs/heads/{branch}")
    run(root, "git", "branch", f"--set-upstream-to=origin/{branch}", branch)
    run(root, "gh", "pr", "create", "--repo", repository, "--head", head, "--assignee", "@me", *args)


def main():
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    operation, *args = sys.argv[1:]
    if operation == "lock":
        lock(root)
    elif operation == "install":
        install(root)
    elif operation == "commit":
        verify(root, git(root, "write-tree"), "smoke-check")
    elif operation == "check":
        verify(root, args[0] if args else "HEAD", args[1] if len(args) > 1 else "check")
    elif operation == "push":
        gate_push(root, args[1] if len(args) == 2 else args[0], sys.stdin.read())
    elif operation == "pr":
        create_pr(root, args[1:] if args[:1] == ["--"] else args)
    else:
        raise ValueError("Usage: git-gate.py lock | install | commit | check [commit] | push <remote> <url> | pr [gh options]")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        print(f"Local gate stopped: {exc}\nRun make install-dev to prepare cached dependencies for the selected snapshot; install Python 3.11, uv, Git, Make, gh and Docker Compose as needed.", file=sys.stderr)
        sys.exit(1)
