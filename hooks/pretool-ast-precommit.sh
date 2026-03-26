#!/usr/bin/env bash
# pretool-ast-precommit.sh — PreToolUse:Bash hook.
# When agent runs `git commit`, validates staged .py and inline Python in .sh files
# with ast.parse. Blocks (exit 2) if any file has syntax errors. Fails open otherwise.

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
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM -- '*.py' 2>/dev/null)

# Get staged shell files
STAGED_SH=$(git diff --cached --name-only --diff-filter=ACM -- '*.sh' 2>/dev/null)

[ -z "$STAGED_PY" ] && [ -z "$STAGED_SH" ] && exit 0

# Validate staged .py files
ERRORS=""
if [ -n "$STAGED_PY" ]; then
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
  done <<< "$STAGED_PY"
fi

# Validate inline Python in staged .sh files
if [ -n "$STAGED_SH" ]; then
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    SH_ERRS=$(python3 -c "
import ast, sys, re

# Extract inline python blocks from shell file
# Only checks single-quote blocks: python3 -c '...' or python3 -c \$'...'
# Double-quote blocks (python3 -c \"...\") are skipped over to avoid false matches
lines = open(sys.argv[1]).readlines()
errors = []
i = 0
while i < len(lines):
    line = lines[i]
    # Skip double-quote delimited python3 -c blocks (not our target pattern,
    # but they can contain ' chars that look like single-quote block starts)
    dq = re.search(r'python3\s+-c\s+\"', line)
    if dq:
        i += 1
        while i < len(lines):
            if lines[i].lstrip().startswith('\"'):
                break
            i += 1
        i += 1
        continue
    # Match: python3 -c ' or python3 -c \$'
    m = re.search(r\"python3\s+-c\s+\\\$?'\", line)
    if m:
        start_line = i + 1  # 1-indexed file line number
        # Get any code after the opening quote on the same line
        after_quote = line[m.end():]
        # Check if this is a single-line block (closing ' on same line)
        close_idx = after_quote.find(\"'\")
        if close_idx >= 0:
            # Single-line: code is between the two quotes
            code = after_quote[:close_idx]
            if code.strip():
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    errors.append(f'inline python3 -c (line {start_line}): {e.msg}')
            i += 1
            continue
        # Multi-line: collect lines until closing quote
        block_lines = []
        if after_quote.strip():
            block_lines.append(after_quote)
        i += 1
        while i < len(lines):
            cur = lines[i]
            # Closing quote: line starts with optional whitespace then '
            stripped = cur.lstrip()
            if stripped.startswith(\"'\"):
                break
            block_lines.append(cur)
            i += 1
        code = ''.join(block_lines)
        # Unescape shell single-quote idiom: '\'' -> ' (end quote, escaped quote, reopen)
        code = code.replace(\"'\\\\''\" , \"'\")
        if code.strip():
            try:
                ast.parse(code)
            except SyntaxError as e:
                offset = start_line + (e.lineno or 1)
                errors.append(f'inline python3 -c (line ~{offset}): {e.msg}')
    i += 1

if errors:
    print('\n'.join(errors))
    sys.exit(1)
" "$f" 2>&1) || ERRORS="${ERRORS}  ${f}: ${SH_ERRS}\n"
  done <<< "$STAGED_SH"
fi

if [ -n "$ERRORS" ]; then
  trap - ERR
  REASON=$(printf "Syntax errors in staged files:\n%b" "$ERRORS")
  ESCAPED=$(echo "$REASON" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
  echo "{\"decision\":\"block\",\"reason\":${ESCAPED}}"
  exit 2
fi

exit 0
