#!/usr/bin/env bash
# posttool-bash-failure-loop.sh — Detect consecutive Bash command failures.
# PostToolUse:Bash hook. Reads JSON tool output from stdin.
# Tracks consecutive failures in /tmp. After N, warns agent to stop retrying.
# Fails open: if this script errors, exit 0.

trap 'exit 0' ERR

# Use PPID (Claude Code process) for session-stable counter. Falls back to fixed name.
COUNTER_FILE="/tmp/claude-bash-failure-count-${PPID:-0}"
THRESHOLD=5

INPUT=$(cat)

# Extract exit code from tool output JSON
# PostToolUse Bash output includes the exit code in the result
EXIT_CODE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Tool output is in 'output' or 'stdout' field; check for error indicators
    output = str(data.get('output', data.get('stdout', '')))
    stderr = str(data.get('stderr', ''))
    exit_code = data.get('exitCode', data.get('exit_code', 0))
    # Consider it a failure if: non-zero exit, or stderr contains error patterns
    if exit_code and exit_code != 0:
        print('fail')
    elif any(p in stderr.lower() for p in ['error', 'failed', 'permission denied', 'not found', 'connection refused']):
        print('fail')
    elif any(p in output.lower() for p in ['traceback (most recent call last)', 'errno', 'httperror', 'connectionerror']):
        print('fail')
    else:
        print('ok')
except:
    print('ok')
" 2>/dev/null)

if [ "$EXIT_CODE" = "fail" ]; then
    # Increment counter
    COUNT=0
    [ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$COUNTER_FILE"

    if [ "$COUNT" -ge "$THRESHOLD" ]; then
        echo "WARNING: $COUNT consecutive Bash command failures detected. You are likely in a retry loop." >&2
        echo "STOP retrying the same approach. Instead:" >&2
        echo "  1. Inform the user what's failing and why" >&2
        echo "  2. Try a fundamentally different approach" >&2
        echo "  3. Or stop and ask for guidance" >&2
        # Reset so the warning fires again after another THRESHOLD failures
        echo "0" > "$COUNTER_FILE"
    fi
else
    # Success — reset counter
    [ -f "$COUNTER_FILE" ] && echo "0" > "$COUNTER_FILE"
fi

exit 0
