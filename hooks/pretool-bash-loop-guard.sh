#!/bin/bash
# pretool-bash-loop-guard.sh — Preflight multiline zsh control syntax
# PreToolUse:Bash hook. Reads JSON tool input from stdin.
# Historical filename retained because global hook configs reference it.
# Uses `zsh -n` to distinguish valid multiline blocks from actual parse errors.
# BLOCKS (exit 2) with guidance; never rewrites commands.

INPUT=$(cat)

# Extract the command field from JSON input
CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null || true)

# If we couldn't extract, let it through
[ -z "$CMD" ] && exit 0

# The sidecar first recognizes the historical multiline shape, then asks zsh to
# parse it without executing it. Exit 0 means a parser-confirmed syntax error.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if SYNTAX_ERROR=$(printf '%s' "$CMD" | python3 "$HOOK_DIR/pretool_bash_loop_guard.py" 2>/dev/null); then
    echo "BLOCKED: Command fails zsh syntax preflight:" >&2
    echo "$SYNTAX_ERROR" >&2
    echo "Complete the control structure (for example, add the missing done/fi)." >&2
    exit 2
fi

exit 0
