#!/bin/bash
# pretool-bash-loop-guard.sh — Block multiline for/while/if that causes zsh parse errors
# PreToolUse:Bash hook. Reads JSON tool input from stdin.
# Deterministic: checks for newlines inside shell control structures.
# BLOCKS (exit 2) with guidance; never rewrites commands.

INPUT=$(cat)

# Extract the command field from JSON input
CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except:
    sys.exit(0)
" 2>/dev/null)

# If we couldn't extract, let it through
[ -z "$CMD" ] && exit 0

# Check for multiline for/while/until/if blocks (the #1 zsh parse error pattern)
# Pattern: line ending with 'do' or 'then', followed by a newline, indicates multiline loop
if echo "$CMD" | python3 -c "
import sys, re
cmd = sys.stdin.read()
# Detect: 'do\n' or 'then\n' followed by content before 'done'/'fi'
# This catches multiline loops but NOT single-line ones
has_multiline = bool(re.search(r'\b(do|then)\s*\n', cmd))
sys.exit(0 if has_multiline else 1)
" 2>/dev/null; then
    echo "BLOCKED: Multiline for/while/if blocks cause zsh parse errors. Use single-line syntax:" >&2
    echo "  for x in *.txt; do echo \"\$x\"; done" >&2
    echo "  while read line; do echo \"\$line\"; done" >&2
    echo "  if [ -f x ]; then echo yes; else echo no; fi" >&2
    echo "Or write a script file and run it." >&2
    exit 2
fi

exit 0
