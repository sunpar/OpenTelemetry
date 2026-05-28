#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-claude-otel.sh --endpoint URL --token TOKEN [--profile normal|max] [--token-capture-profile normal|max] [--output FILE]

Writes a shell-compatible Claude Code OpenTelemetry env file and prints the
source command. The installer does not edit shell startup files.
EOF
}

endpoint=""
token=""
profile="normal"
token_capture_profile="normal"
output_path="./claude.otel.env"

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
    --token-capture-profile)
      token_capture_profile="${2:-}"
      shift 2
      ;;
    --output)
      output_path="${2:-}"
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
  normal|max)
    ;;
  *)
    printf 'Unsupported profile: %s\n' "$profile" >&2
    exit 2
    ;;
esac

case "$token_capture_profile" in
  normal|max)
    ;;
  *)
    printf 'Unsupported token capture profile: %s\n' "$token_capture_profile" >&2
    exit 2
    ;;
esac

if [[ "$profile" == "max" && "$token_capture_profile" != "max" ]]; then
  printf '%s\n' 'Profile max requires --token-capture-profile max.' >&2
  exit 2
fi

endpoint="${endpoint%/}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
normal_template="$repo_root/templates/claude.env"
max_template="$repo_root/templates/claude.max-capture.env"

mkdir -p "$(dirname "$output_path")"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

awk \
  -v endpoint="$endpoint" \
  -v token="$token" '
    {
      gsub(/\{\{ENDPOINT\}\}/, endpoint)
      gsub(/\{\{TOKEN\}\}/, token)
      print
    }
  ' "$normal_template" > "$tmp"

if [[ "$profile" == "max" ]]; then
  printf '\n' >> "$tmp"
  cat "$max_template" >> "$tmp"
fi

mv "$tmp" "$output_path"
chmod 600 "$output_path"

printf 'Claude Code env written: %s\n' "$output_path"
printf 'Profile: %s\n' "$profile"
printf 'Run: source %q\n' "$output_path"
