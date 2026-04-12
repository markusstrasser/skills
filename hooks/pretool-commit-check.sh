#!/usr/bin/env bash
# pretool-commit-check.sh — Check git commit messages before execution.
# PreToolUse:Bash hook. Advisory for most checks, blocks Co-Authored-By.
# Checks: no Co-Authored-By, has [prefix], Type: trailer, body presence,
# em-dash in subject, governance trailers.

trap 'exit 0' ERR

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_INPUT=$(cat)

# Parse in separate Python file (avoids bash quoting hell)
RESULT=$(echo "$HOOK_INPUT" | python3 "$HOOK_DIR/commit-check-parse.py" 2>/dev/null) || exit 0

# Not a commit
[ "$RESULT" = "SKIP" ] && exit 0
[ "$RESULT" = "OK" ] && exit 0

# Blocking
if echo "$RESULT" | grep -q "^BLOCK:"; then
  ~/Projects/skills/hooks/hook-trigger-log.sh "commit-check" "block" "$(echo "$RESULT" | sed 's/^BLOCK://' | head -c 100)" 2>/dev/null || true
  msg=$(echo "$RESULT" | sed 's/^BLOCK://')
  echo "[commit-check]: BLOCKED: $msg" >&2
  echo "$msg"
  exit 2
fi

# Advisory warnings
if echo "$RESULT" | grep -q "^WARN:"; then
  WARN_TEXT=$(echo "$RESULT" | sed 's/^WARN://')

  # Body warning: required for research/decisions, advisory for multi-file commits
  STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  CONCEPT_FILES=$(git diff --cached --name-only 2>/dev/null | grep -cE '^(research/|decisions/|docs/research/)' | tr -d ' ')
  if [ "$CONCEPT_FILES" -gt 0 ]; then
    WARN_TEXT=$(echo "$WARN_TEXT" | sed "s/NOBODY/Concept files (research\\/decisions) staged — body REQUIRED. Name the concept affected and what changed./g")
  elif [ "$STAGED_COUNT" -le 1 ]; then
    WARN_TEXT=$(echo "$WARN_TEXT" | sed 's/ | NOBODY//g; s/NOBODY | //g; s/NOBODY//g')
  else
    WARN_TEXT=$(echo "$WARN_TEXT" | sed "s/NOBODY/${STAGED_COUNT} files staged but no body — add trigger, changes, impact./g")
  fi

  # Governance trailer check
  GOV=$(git diff --cached --name-only 2>/dev/null | grep -iE '(CLAUDE\.md|MEMORY\.md|improvement-log|hooks/)' | head -1)
  if [ -n "$GOV" ]; then
    echo "$RESULT" | grep -q "Evidence:" || WARN_TEXT="${WARN_TEXT} | Governance file (${GOV}) needs Evidence: trailer."
    echo "$RESULT" | grep -q "Affects:" || WARN_TEXT="${WARN_TEXT} | Governance file needs Affects: trailer."
  fi

  # Clean up empty segments
  WARN_TEXT=$(echo "$WARN_TEXT" | sed 's/^ | //; s/ | $//; s/ |  | / | /g')

  if [ -n "$WARN_TEXT" ] && [ "$WARN_TEXT" != " " ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "commit-check" "warn" "${WARN_TEXT:0:100}" 2>/dev/null || true
    ESCAPED=$(echo "$WARN_TEXT" | sed 's/"/\\"/g' | tr '\n' ' ')
    echo "{\"additionalContext\": \"COMMIT CHECK: ${ESCAPED}\"}"
  fi
fi

exit 0
