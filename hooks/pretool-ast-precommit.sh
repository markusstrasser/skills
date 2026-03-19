#!/usr/bin/env bash
# pretool-ast-precommit.sh — PreToolUse:Bash hook.
# When agent runs `git commit`, validates staged .py files with ast.parse.
# Blocks (exit 2) if any file has syntax errors. Fails open otherwise.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract command from tool input
CMD=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get("tool_input", {}).get("command", ""))
except Exception:
    pass
' 2>/dev/null) || exit 0

# Only trigger on git commit commands
echo "$CMD" | grep -qE '^\s*git\s+commit' || exit 0

# Get staged Python files
STAGED=$(git diff --cached --name-only --diff-filter=ACM -- '*.py' 2>/dev/null)
[ -z "$STAGED" ] && exit 0

# Validate each file
ERRORS=""
while IFS= read -r f; do
  [ -f "$f" ] || continue
  ERR=$(python3 -c "
import ast, sys
try:
    ast.parse(open(sys.argv[1]).read())
except SyntaxError as e:
    print(f'{e.msg} (line {e.lineno})')
    sys.exit(1)
" "$f" 2>&1) || ERRORS="${ERRORS}  ${f}: ${ERR}\n"
done <<< "$STAGED"

if [ -n "$ERRORS" ]; then
  trap - ERR
  REASON=$(printf "Syntax errors in staged .py files:\n%b" "$ERRORS")
  ESCAPED=$(echo "$REASON" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
  echo "{\"decision\":\"block\",\"reason\":${ESCAPED}}"
  exit 2
fi

exit 0
