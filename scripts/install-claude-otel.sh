#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-claude-otel.sh --endpoint URL --token TOKEN [--profile normal|max] [--output FILE]

Writes a shell-compatible Claude Code OpenTelemetry env file and prints the
source command. The installer does not edit shell startup files.

The max profile is refused until the installer can verify trusted token
metadata from auth-api or otelctl.
EOF
}

unknown_argument() {
  case "$1" in
    --token=*|--token)
      printf '%s\n' 'Unknown or malformed token argument: --token=<redacted>' >&2
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      ;;
  esac
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
    --token=*)
      token="${1#--token=}"
      shift
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
    --output=*)
      output_path="${1#--output=}"
      shift
      ;;
    --endpoint=*)
      endpoint="${1#--endpoint=}"
      shift
      ;;
    --profile=*)
      profile="${1#--profile=}"
      shift
      ;;
    --token-capture-profile=*)
      token_capture_profile="${1#--token-capture-profile=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      unknown_argument "$1"
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

if [[ "$profile" == "max" ]]; then
  printf '%s\n' 'Profile max requires trusted token metadata with capture_profile=max; this installer cannot verify token metadata yet.' >&2
  exit 2
fi

endpoint="${endpoint%/}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
normal_template="$repo_root/templates/claude.env"
max_template="$repo_root/templates/claude.max-capture.env"
otlp_headers="Authorization=Bearer $token"

printf -v endpoint_shell '%q' "$endpoint"
printf -v otlp_headers_shell '%q' "$otlp_headers"

render_template() {
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line//'{{ENDPOINT}}'/$endpoint_shell}"
    line="${line//'{{OTLP_HEADERS}}'/$otlp_headers_shell}"
    printf '%s\n' "$line"
  done < "$1"
}

mkdir -p "$(dirname "$output_path")"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

render_template "$normal_template" > "$tmp"

if [[ "$profile" == "max" ]]; then
  printf '\n' >> "$tmp"
  cat "$max_template" >> "$tmp"
fi

mv "$tmp" "$output_path"
chmod 600 "$output_path"

printf 'Claude Code env written: %s\n' "$output_path"
printf 'Profile: %s\n' "$profile"
printf 'Run: source %q\n' "$output_path"
