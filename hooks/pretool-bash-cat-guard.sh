#!/bin/bash
# pretool-bash-cat-guard.sh — Block $(cat <literal-path>) where the path doesn't exist.
# PreToolUse:Bash hook. Reads JSON tool input from stdin.
#
# Why: a dispatch brief assembled via `codex exec "$(cat common.md spec.md)"` SILENTLY
# degrades to a half-brief when a file is missing (cat writes to stderr, $() keeps going) —
# 2026-07-10 arc-agi: two 3-worker codex waves built off-spec games from a directory name
# because a hook-blocked write had left the spec files absent. Same failure class as
# watcher-filter positive controls: verify the brief EXISTS before spending on it.
#
# Deterministic + conservative: only LITERAL paths inside $(cat ...) are checked; anything
# containing $, `, or glob chars is skipped; paths that appear as a redirect target (> path)
# earlier in the same command are skipped (created-before-use). BLOCKS (exit 2) with the
# missing path named; never rewrites.

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null || true)
[ -z "$CMD" ] && exit 0

# Fast reject: no "$(cat " substring, nothing to do.
case "$CMD" in
  *'$(cat '*) ;;
  *) exit 0 ;;
esac

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)
MISSING=$(printf '%s' "$CMD" | CAT_GUARD_CWD="$CWD" python3 "$HOOK_DIR/pretool_bash_cat_guard.py" 2>/dev/null || true)

if [ -n "$MISSING" ]; then
    echo "BLOCKED: \$(cat ...) references file(s) that do not exist — the command would silently run with a truncated/empty substitution:" >&2
    printf '%s\n' "$MISSING" | sed 's/^/  missing: /' >&2
    echo "Create the file first (verify with wc -c), or fix the path. If the file is created earlier in this same command via a redirect, this guard skips it — heredocs inside \$( ) are not detected, restructure instead." >&2
    exit 2
fi
exit 0
