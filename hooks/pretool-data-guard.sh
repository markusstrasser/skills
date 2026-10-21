#!/usr/bin/env bash
# pretool-data-guard.sh — Generalized data file protection hook.
# Deploy as PreToolUse hook on Write|Edit (and optionally Bash).
# Takes protected path patterns as arg or env var.
# Exit 2 = block. Exit 0 = pass. Fails CLOSED on error (constitution P10: protected-data writes);
# wire with "onFailure": "block" so a hook that cannot start blocks too.

trap 'echo "data-guard: internal error at line $LINENO — blocking (fail closed)" >&2; exit 2' ERR

INPUT=$(cat)

# grep -E exits 2 on an invalid pattern; inside `if`/`||` that would read as "no match".
matches() { local rc=0; printf '%s\n' "$1" | grep -qE "$2" || rc=$?
  [ "$rc" -gt 1 ] && { echo "data-guard: invalid pattern '$2' — blocking (fail closed)" >&2; exit 2; }
  return "$rc"; }

# Protected path patterns (configurable via arg or env)
PROTECTED="${1:-${PROTECTED_PATHS:-datasets/|\.parquet|\.duckdb}}"

# Block message (configurable via env)
BLOCK_MSG="${BLOCK_MSG:-BLOCKED: Cannot modify protected data files.}"

# Extract file path from hook input
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')

[ -z "$FPATH" ] && exit 0

if matches "$FPATH" "$PROTECTED"; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "data-guard" "block" "$FPATH" 2>/dev/null || true
    echo "$BLOCK_MSG" >&2
    exit 2
fi

exit 0
