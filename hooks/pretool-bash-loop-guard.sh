#!/bin/bash
# pretool-bash-loop-guard.sh — Block multiline for/while/if that causes zsh parse errors
# PreToolUse:Bash hook. Reads JSON tool input from stdin.
# Deterministic: checks for newlines inside shell control structures.
# BLOCKS (exit 2) with guidance; never rewrites commands.

INPUT=$(cat)

# Extract the command field from JSON input
CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null || true)

# If we couldn't extract, let it through
[ -z "$CMD" ] && exit 0

# Check for multiline for/while/until/if blocks (the #1 zsh parse error pattern):
# line ending with 'do' or 'then' followed by a newline. Heredoc bodies and quoted-string
# spans are stripped first (both opaque to the shell parser — false positives 2026-06-10
# heredoc payload, 2026-07-03 commit-message prose ending a line on 'then').
# Logic lives in the sidecar (testable; escaping a quote scanner inside a bash
# double-quoted python -c string is its own bug class): exit 0 = multiline found.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if printf '%s' "$CMD" | python3 "$HOOK_DIR/pretool_bash_loop_guard.py" 2>/dev/null; then
    echo "BLOCKED: Multiline for/while/if blocks cause zsh parse errors. Use single-line syntax:" >&2
    echo "  for x in *.txt; do echo \"\$x\"; done" >&2
    echo "  while read line; do echo \"\$line\"; done" >&2
    echo "  if [ -f x ]; then echo yes; else echo no; fi" >&2
    echo "Or write a script file and run it." >&2
    exit 2
fi

exit 0
