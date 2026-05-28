#!/usr/bin/env bash
set -euo pipefail

codex_home="${CODEX_HOME:-"$HOME/.codex"}"
config_path="${CODEX_CONFIG:-"$codex_home/config.toml"}"

if [[ ! -f "$config_path" ]]; then
  exit 0
fi

timestamp="${AOTEL_BACKUP_TIMESTAMP:-"$(date +%Y%m%d%H%M%S)"}"
backup_path="${config_path}.bak.${timestamp}"

if [[ -e "$backup_path" ]]; then
  suffix=1
  while [[ -e "${backup_path}.${suffix}" ]]; do
    suffix=$((suffix + 1))
  done
  backup_path="${backup_path}.${suffix}"
fi

cp "$config_path" "$backup_path"
printf '%s\n' "$backup_path"
