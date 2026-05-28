# Test Baseline

Last updated: 2026-05-28

## Baseline Summary

The repository is currently documentation-only. No source implementation, package
manager metadata, test runner, Compose files, or CI workflow exists yet.

## Commands Run

```sh
find . -maxdepth 3 -type f \( -name 'package.json' -o -name 'pyproject.toml' -o -name 'requirements.txt' -o -name 'go.mod' -o -name 'Cargo.toml' -o -name 'Makefile' -o -name 'justfile' -o -name 'docker-compose*.yml' -o -name '*.yaml' -o -name '*.yml' \) -print | sort
```

Result: no package/build/Compose files found.

```sh
git diff --check
```

Result: clean after generated artifacts are validated.

```sh
/opt/homebrew/bin/python3.11 - <<'PY'
from pathlib import Path
import re, tomllib
text = Path('docs/onboarding.md').read_text()
for i, block in enumerate(re.findall(r'```toml\n(.*?)\n```', text, re.S), 1):
    tomllib.loads(block.replace('<TOKEN>', 'TOKEN'))
    print(f'toml block {i} ok')
PY
```

Result: onboarding TOML snippets parse.

```sh
python3 internal markdown link check over README.md and docs/**/*.md
```

Result: internal Markdown links pass.

## Known Non-Executable Commands

These commands are planned contracts and are expected to fail until later tasks
create implementation files:

- `make signoz-up`
- `make up`
- `make user EMAIL=alice@example.com TEAM=quant-dev`
- `make token EMAIL=alice@example.com`
- `make smoke TOKEN=<issued-token>`
- `python -m pytest`
- `docker compose -f compose/docker-compose.gateway.yml config`
- `docker compose -f compose/docker-compose.signoz.yml config`

## Environment Assumptions

- macOS local development environment.
- `zsh` shell.
- Python 3.11 available at `/opt/homebrew/bin/python3.11`.
- Codex CLI available for `codex doctor` config-load checks.
- Docker availability has not been verified in this baseline.

## Failure List

No implementation test failures are recorded because no implementation test
suite exists yet.
