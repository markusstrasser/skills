#!/usr/bin/env bash
# PostToolUse hook — matcher: Skill
# Logs skill completion with duration and exit status.

set -euo pipefail

LOGFILE="$HOME/.claude/skill-triggers.jsonl"
STARTFILE="/tmp/claude-skill-start-$$"

# Extract skill name from tool input
SKILL=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('skill', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION="${CLAUDE_SESSION_ID:-unknown}"

# Calculate duration
DURATION_MS=0
if [ -f "$STARTFILE" ]; then
    START_NS=$(cat "$STARTFILE")
    NOW_NS=$(date +%s%N)
    DURATION_MS=$(( (NOW_NS - START_NS) / 1000000 ))
    rm -f "$STARTFILE"
fi

# Check if tool result indicates error (exit_code from CLAUDE_TOOL_RESULT)
EXIT_CODE=0
if echo "${CLAUDE_TOOL_RESULT:-}" | grep -qi "error\|failed\|exception"; then
    EXIT_CODE=1
fi

printf '{"ts":"%s","event":"skill_complete","skill":"%s","session":"%s","duration_ms":%d,"exit_code":%d}\n' \
    "$TS" "$SKILL" "$SESSION" "$DURATION_MS" "$EXIT_CODE" >> "$LOGFILE"
