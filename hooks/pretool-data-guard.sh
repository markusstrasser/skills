#!/usr/bin/env bash
# pretool-data-guard.sh — Generalized data file protection hook.
# Deploy as PreToolUse hook on Write|Edit (and optionally Bash).
# Takes protected path patterns as arg or env var.
# Exit 2 = block. Exit 0 = pass. Fails open on error.

# Trap errors — fail open
trap 'exit 0' ERR

INPUT=$(cat)

# Protected path patterns (configurable via arg or env)
PROTECTED="${1:-${PROTECTED_PATHS:-datasets/|\.parquet|\.duckdb}}"

# Block message (configurable via env)
BLOCK_MSG="${BLOCK_MSG:-BLOCKED: Cannot modify protected data files.}"

# Extract file path from hook input
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')

[ -z "$FPATH" ] && exit 0

if echo "$FPATH" | grep -qE "$PROTECTED"; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "data-guard" "block" "$FPATH" 2>/dev/null || true
    echo "$BLOCK_MSG" >&2
    exit 2
fi

exit 0
