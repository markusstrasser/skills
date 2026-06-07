#!/usr/bin/env bash
# PreToolUse hook — matcher: Skill
# Logs skill invocations to ~/.claude/skill-triggers.jsonl
# Also writes start timestamp for duration calculation by posttool hook.

set -euo pipefail

LOGFILE="$HOME/.claude/skill-triggers.jsonl"
STARTFILE="/tmp/claude-skill-start-$$"

# Read stdin once; fall back to env var (Codex sets CLAUDE_TOOL_INPUT)
INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"

# Extract skill name from tool input
SKILL=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('tool_input', d) or {}).get('skill', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)

ARGS=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('tool_input', d) or {}).get('args', ''))
except:
    print('')
" 2>/dev/null)

# Extract first word of args as mode (empty for skills without modes)
MODE=$(echo "$ARGS" | awk '{print $1}')

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"
PROJECT=$(basename "${CLAUDE_PROJECT_DIR:-$(pwd)}")

# Write start time for duration calc
date +%s%N > "$STARTFILE"

# Log invocation
printf '{"ts":"%s","event":"skill_invoke","skill":"%s","mode":"%s","args":"%s","session":"%s","project":"%s"}\n' \
    "$TS" "$SKILL" "$MODE" "$ARGS" "$SESSION" "$PROJECT" >> "$LOGFILE"
