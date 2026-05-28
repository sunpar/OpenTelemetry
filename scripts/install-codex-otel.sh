#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-codex-otel.sh --endpoint URL --token TOKEN [--profile normal|max]

Installs the managed Agent OpenTelemetry [otel] block into CODEX_HOME/config.toml.
EOF
}

endpoint=""
token=""
profile="normal"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --endpoint)
      endpoint="${2:-}"
      shift 2
      ;;
    --token)
      token="${2:-}"
      shift 2
      ;;
    --profile)
      profile="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$endpoint" ]]; then
  printf '%s\n' 'Missing required --endpoint' >&2
  usage >&2
  exit 2
fi

if [[ -z "$token" ]]; then
  printf '%s\n' 'Missing required --token' >&2
  usage >&2
  exit 2
fi

case "$profile" in
  normal)
    log_user_prompt="false"
    ;;
  max)
    log_user_prompt="true"
    ;;
  *)
    printf 'Unsupported profile: %s\n' "$profile" >&2
    exit 2
    ;;
esac

endpoint="${endpoint%/}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
template_path="$repo_root/templates/codex.config.toml"
codex_home="${CODEX_HOME:-"$HOME/.codex"}"
config_path="${CODEX_CONFIG:-"$codex_home/config.toml"}"
start_marker="# >>> agent-otel managed codex telemetry"
end_marker="# <<< agent-otel managed codex telemetry"

mkdir -p "$codex_home"

backup_path=""
if [[ -f "$config_path" ]]; then
  backup_path="$(
    CODEX_HOME="$codex_home" CODEX_CONFIG="$config_path" \
      "$script_dir/backup-codex-config.sh"
  )"
fi

existing_tmp="$(mktemp)"
rendered_tmp="$(mktemp)"
output_tmp="$(mktemp)"
trap 'rm -f "$existing_tmp" "$rendered_tmp" "$output_tmp"' EXIT

if [[ -f "$config_path" ]]; then
  awk -v start="$start_marker" -v end="$end_marker" '
    $0 == start { skip = 1; next }
    $0 == end { skip = 0; next }
    !skip { print }
  ' "$config_path" > "$existing_tmp"
else
  : > "$existing_tmp"
fi

awk \
  -v endpoint="$endpoint" \
  -v token="$token" \
  -v log_user_prompt="$log_user_prompt" '
    {
      gsub(/\{\{ENDPOINT\}\}/, endpoint)
      gsub(/\{\{TOKEN\}\}/, token)
      gsub(/\{\{LOG_USER_PROMPT\}\}/, log_user_prompt)
      print
    }
  ' "$template_path" > "$rendered_tmp"

{
  if [[ -s "$existing_tmp" ]]; then
    cat "$existing_tmp"
    printf '\n'
  fi
  printf '%s\n' "$start_marker"
  cat "$rendered_tmp"
  printf '%s\n' "$end_marker"
} > "$output_tmp"

mv "$output_tmp" "$config_path"
chmod 600 "$config_path"

printf 'Codex config updated: %s\n' "$config_path"
if [[ -n "$backup_path" ]]; then
  printf 'Backup created: %s\n' "$backup_path"
fi
printf 'Endpoint: %s\n' "$endpoint"
printf 'Profile: %s\n' "$profile"
