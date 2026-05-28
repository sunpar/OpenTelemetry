#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".pytest_cache", ".ruff_cache", ".venv", ".vendor", ".signoz"}
TEXT_SUFFIXES = {
    ".env",
    ".example",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def tracked_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name == "Makefile" or path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return sorted(files)


def check_ascii_and_trailing_whitespace() -> list[str]:
    failures: list[str] = []
    for path in tracked_text_files():
        relative = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="ascii")
        except UnicodeDecodeError as exc:
            failures.append(f"{relative}: non-ASCII byte near offset {exc.start}")
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.rstrip(" \t") != line:
                failures.append(f"{relative}:{lineno}: trailing whitespace")
    return failures


def check_markdown_links() -> list[str]:
    failures: list[str] = []
    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("**/*.md"))]
    markdown_files.extend(sorted((ROOT / "infra").glob("**/README.md")))

    for path in markdown_files:
        text = path.read_text(encoding="ascii")
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            raw_link = match.group(1).strip()
            if raw_link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            link = raw_link.split("#", 1)[0]
            if not link:
                continue
            target = (path.parent / link).resolve()
            if not target.exists():
                failures.append(f"{path.relative_to(ROOT)} -> {raw_link}")
    return failures


def check_onboarding_toml_snippets() -> list[str]:
    failures: list[str] = []
    text = (ROOT / "docs/onboarding.md").read_text(encoding="ascii")
    for index, block in enumerate(re.findall(r"```toml\n(.*?)\n```", text, re.S), 1):
        try:
            tomllib.loads(block.replace("<TOKEN>", "TOKEN"))
        except tomllib.TOMLDecodeError as exc:
            failures.append(f"docs/onboarding.md TOML block {index}: {exc}")
    return failures


def check_dashboard_json() -> list[str]:
    failures: list[str] = []
    for path in sorted((ROOT / "infra/signoz/dashboards").glob("*.json")):
        try:
            json.loads(path.read_text(encoding="ascii"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
    return failures


def check_shell_syntax() -> list[str]:
    failures: list[str] = []
    for path in sorted((ROOT / "scripts").glob("*.sh")):
        result = subprocess.run(
            ["bash", "-n", str(path)],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            failures.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")
    return failures


def main() -> int:
    checks = {
        "ascii/trailing whitespace": check_ascii_and_trailing_whitespace,
        "markdown links": check_markdown_links,
        "onboarding TOML snippets": check_onboarding_toml_snippets,
        "dashboard JSON": check_dashboard_json,
        "shell syntax": check_shell_syntax,
    }

    failures: list[str] = []
    for name, check in checks.items():
        check_failures = check()
        if check_failures:
            failures.extend(f"{name}: {failure}" for failure in check_failures)
        else:
            print(f"ok {name}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
