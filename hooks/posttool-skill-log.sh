#!/usr/bin/env bash
# PostToolUse hook — matcher: Skill
# Logs skill invocation with project, duration, exit status.
# Data feeds skill-usage-report.py (30-day analysis, SKILL0 pattern).

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

ARGS=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('args', ''))
except:
    print('')
" 2>/dev/null)

# Extract first word of args as mode (empty for skills without modes)
MODE=$(echo "$ARGS" | awk '{print $1}')

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION="${CLAUDE_SESSION_ID:-unknown}"
PROJECT=$(basename "${CLAUDE_CWD:-$(pwd)}")

# Calculate duration (macOS date lacks %N — fallback gracefully)
DURATION_MS=0
if [ -f "$STARTFILE" ]; then
    START_NS=$(cat "$STARTFILE")
    NOW_NS=$(python3 -c "import time; print(int(time.time_ns()))" 2>/dev/null || echo 0)
    if [ "$NOW_NS" -gt 0 ] && [ "$START_NS" -gt 0 ] 2>/dev/null; then
        DURATION_MS=$(( (NOW_NS - START_NS) / 1000000 ))
    fi
    rm -f "$STARTFILE"
fi

# Check if tool result indicates error
EXIT_CODE=0
if echo "${CLAUDE_TOOL_RESULT:-}" | grep -qi "error\|failed\|exception"; then
    EXIT_CODE=1
fi

printf '{"ts":"%s","event":"skill_complete","skill":"%s","mode":"%s","session":"%s","project":"%s","duration_ms":%d,"exit_code":%d}\n' \
    "$TS" "$SKILL" "$MODE" "$SESSION" "$PROJECT" "$DURATION_MS" "$EXIT_CODE" >> "$LOGFILE"
