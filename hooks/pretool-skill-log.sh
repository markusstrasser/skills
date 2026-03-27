#!/usr/bin/env bash
# PreToolUse hook — matcher: Skill
# Logs skill invocations to ~/.claude/skill-triggers.jsonl
# Also writes start timestamp for duration calculation by posttool hook.

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

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION="${CLAUDE_SESSION_ID:-unknown}"
PROJECT=$(basename "${CLAUDE_PROJECT_DIR:-$(pwd)}")

# Write start time for duration calc
date +%s%N > "$STARTFILE"

# Log invocation
printf '{"ts":"%s","event":"skill_invoke","skill":"%s","args":"%s","session":"%s","project":"%s"}\n' \
    "$TS" "$SKILL" "$ARGS" "$SESSION" "$PROJECT" >> "$LOGFILE"
