#!/usr/bin/env bash
# pretool-commit-check.sh — Check git commit messages before execution.
# PreToolUse:Bash hook. Advisory only (exit 0, uses additionalContext).
# Checks: no Co-Authored-By: Claude, has [prefix], trailers on governance files.

trap 'exit 0' ERR

INPUT=$(cat)

# Only check git commit commands
CMD=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null)

# Skip if not a git commit
echo "$CMD" | grep -q "git commit" || exit 0

WARNINGS=""

# Check for Co-Authored-By: Claude
if echo "$CMD" | grep -qi "Co-Authored-By.*Claude"; then
  WARNINGS="${WARNINGS}BLOCK: Commit contains Co-Authored-By: Claude — remove it per global CLAUDE.md rules. "
  echo "$WARNINGS"
  exit 2
fi

# Check for [prefix] format
if echo "$CMD" | grep -q '\-m' && ! echo "$CMD" | grep -qE '\[([-a-zA-Z0-9]+)\]'; then
  WARNINGS="${WARNINGS}Missing [feature-name] prefix in commit message. "
fi

# Check if governance files are staged — if so, require trailers
GOVERNANCE_STAGED=$(cd "$(pwd)" && git diff --cached --name-only 2>/dev/null | grep -iE '(CLAUDE\.md|MEMORY\.md|improvement-log|hooks/)' | head -5)
if [ -n "$GOVERNANCE_STAGED" ]; then
  if ! echo "$CMD" | grep -qi "Evidence:"; then
    WARNINGS="${WARNINGS}Governance files staged ($GOVERNANCE_STAGED) but commit lacks Evidence: trailer. "
  fi
  if ! echo "$CMD" | grep -qi "Affects:"; then
    WARNINGS="${WARNINGS}Governance files staged but commit lacks Affects: trailer. "
  fi
fi

if [ -n "$WARNINGS" ]; then
  echo "{\"additionalContext\": \"COMMIT CHECK: $WARNINGS\"}"
fi

exit 0
