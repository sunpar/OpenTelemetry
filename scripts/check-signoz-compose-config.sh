#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_cmd_text="${DOCKER_COMPOSE:-docker compose}"
read -r -a compose_cmd <<< "$compose_cmd_text"

repo_path() {
	case "$1" in
		/*) printf '%s\n' "$1" ;;
		*) printf '%s\n' "$root_dir/$1" ;;
	esac
}

signoz_vendor_dir="$(repo_path "${SIGNOZ_VENDOR_DIR:-.vendor/signoz}")"
signoz_compose_override="$(repo_path "${SIGNOZ_COMPOSE_OVERRIDE:-compose/docker-compose.signoz.override.yml}")"
upstream_compose="$signoz_vendor_dir/deploy/docker/docker-compose.yaml"

if [[ -f "$upstream_compose" ]]; then
	"${compose_cmd[@]}" -f "$upstream_compose" -f "$signoz_compose_override" config >/dev/null
	exit 0
fi

tmp_compose="$(mktemp)"
trap 'rm -f "$tmp_compose"' EXIT

cat > "$tmp_compose" <<'YAML'
name: upstream-signoz
services:
  signoz:
    image: busybox
    networks:
      - signoz-net
    ports:
      - "8080:8080"
  otel-collector:
    image: busybox
    networks:
      - signoz-net
    ports:
      - "4317:4317"
      - "4318:4318"
networks:
  signoz-net:
    name: signoz-net
YAML

"${compose_cmd[@]}" -f "$tmp_compose" -f "$signoz_compose_override" config >/dev/null
