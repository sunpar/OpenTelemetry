# Test Commands

Last updated: 2026-05-28

## Current Test Status

No runnable implementation exists yet. There are no source directories, package
manager files, test directories, CI workflows, Compose files, or Make targets.

Current verification is limited to documentation and snippet checks.

## Package Manager Discovery

Commands used for discovery:

```sh
find . -maxdepth 3 -type f \( \
  -name 'package.json' -o \
  -name 'pyproject.toml' -o \
  -name 'requirements.txt' -o \
  -name 'go.mod' -o \
  -name 'Cargo.toml' -o \
  -name 'Makefile' -o \
  -name 'justfile' -o \
  -name 'docker-compose*.yml' -o \
  -name '*.yaml' -o \
  -name '*.yml' \
\) -print | sort
```

Current result: no files found.

## Documentation Verification

Run from repository root.

Parse TOML snippets in `docs/onboarding.md`:

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

Check generated Codex config shape loads:

```sh
tmp=$(mktemp -d)
mkdir -p "$tmp"
/opt/homebrew/bin/python3.11 - <<'PY' > "$tmp/config.toml"
from pathlib import Path
import re
text = Path('docs/onboarding.md').read_text()
block = re.findall(r'```toml\n(.*?)\n```', text, re.S)[0]
print(block.replace('<TOKEN>', 'TOKEN'))
PY
CODEX_HOME="$tmp" codex doctor --json >/tmp/codex-doctor-out 2>/tmp/codex-doctor-err
rm -rf "$tmp"
```

`codex doctor` may return nonzero when the temporary `CODEX_HOME` has no auth
credentials. For this check, inspect the JSON `config.load` check and require:

```text
status: ok
summary: config loaded
config.toml parse: ok
```

Check internal Markdown links:

```sh
python3 - <<'PY'
from pathlib import Path
import re
bad = []
for p in [Path('README.md'), *Path('docs').glob('**/*.md')]:
    text = p.read_text()
    for m in re.finditer(r'\[[^\]]+\]\(([^)#][^)]+)\)', text):
        link = m.group(1)
        if link.startswith(('http://', 'https://', 'mailto:')):
            continue
        target = (p.parent / link).resolve()
        if not target.exists():
            bad.append((str(p), link))
if bad:
    for path, link in bad:
        print(f'{path} -> {link}')
    raise SystemExit(1)
print('internal markdown links ok')
PY
```

Check whitespace and ASCII:

```sh
git diff --check
rg -n '[ \t]+$' README.md docs
LC_ALL=C rg -n '[^\x00-\x7F]' README.md docs
```

## Planned Milestone Verification

These commands are documented contracts, not runnable commands yet.

Milestone 1:

```sh
make signoz-up
make up
make user EMAIL=alice@example.com TEAM=quant-dev
make token EMAIL=alice@example.com
make smoke TOKEN=<issued-token>
curl -i http://localhost:8088/v1/logs -H 'Authorization: Bearer invalid'
curl -fsS http://localhost:8088/healthz
docker compose -f compose/docker-compose.gateway.yml ps
docker compose -f compose/docker-compose.gateway.yml logs -f auth-api
docker compose -f compose/docker-compose.gateway.yml logs -f nginx
docker compose -f compose/docker-compose.gateway.yml logs -f otel-collector
```

Milestone 2:

```sh
bash scripts/install-codex-otel.sh --endpoint "$ENDPOINT" --token "$TOKEN"
```

Milestone 3:

```sh
bash scripts/install-claude-otel.sh --endpoint "$ENDPOINT" --token "$TOKEN"
```

## CI Status

No CI workflow exists. When CI is added, it needs jobs for:

- docs link/snippet checks
- auth-api tests
- `otelctl` CLI tests
- Compose config validation
- Collector config validation
- installer shell checks
- smoke-test execution against the local gateway stack

## Known Unknowns

- Package manager commands are not defined yet.
- Build commands are not defined yet.
- Lint commands are not defined yet.
- Unit and integration test runners are not defined yet.
- CI provider and job matrix are not defined yet.
