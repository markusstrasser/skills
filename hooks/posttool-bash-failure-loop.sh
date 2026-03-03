#!/usr/bin/env bash
# posttool-bash-failure-loop.sh — Detect consecutive Bash failures with targeted correction.
# PostToolUse:Bash hook. Reads JSON tool output from stdin.
# Tracks consecutive failures in /tmp. After THRESHOLD, extracts the specific error
# and injects targeted correction advice (not just "stop retrying").
# Based on AgentDebug finding: targeted correction +24% over blind retry.
# Fails open: if this script errors, exit 0.

trap 'exit 0' ERR

# Use PPID (Claude Code process) for session-stable counter. Falls back to fixed name.
COUNTER_FILE="/tmp/claude-bash-failure-count-${PPID:-0}"
ERROR_FILE="/tmp/claude-bash-last-error-${PPID:-0}"
THRESHOLD=5

INPUT=$(cat)

# Extract failure status and error details from tool output JSON
RESULT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    output = str(data.get('tool_result', data.get('output', data.get('stdout', ''))))
    stderr = str(data.get('stderr', ''))
    exit_code = data.get('exitCode', data.get('exit_code', 0))

    failed = False
    error_msg = ''

    if exit_code and exit_code != 0:
        failed = True
        # Extract the most useful error line
        for line in (stderr or output).split('\n'):
            line = line.strip()
            if line and any(p in line.lower() for p in ['error', 'failed', 'denied', 'not found', 'no such', 'cannot', 'traceback']):
                error_msg = line[:200]
                break
        if not error_msg:
            error_msg = (stderr or output).strip().split('\n')[-1][:200]
    elif any(p in stderr.lower() for p in ['error', 'failed', 'permission denied', 'not found', 'connection refused']):
        failed = True
        for line in stderr.split('\n'):
            line = line.strip()
            if line and any(p in line.lower() for p in ['error', 'failed', 'denied', 'not found']):
                error_msg = line[:200]
                break
    elif any(p in output.lower() for p in ['traceback (most recent call last)', 'errno', 'httperror', 'connectionerror']):
        failed = True
        lines = output.strip().split('\n')
        # For tracebacks, grab the last 2 lines (exception type + message)
        error_msg = ' | '.join(l.strip() for l in lines[-2:])[:200]

    if failed:
        print(f'fail|{error_msg}')
    else:
        print('ok|')
except:
    print('ok|')
" 2>/dev/null)

STATUS="${RESULT%%|*}"
ERROR_MSG="${RESULT#*|}"

if [ "$STATUS" = "fail" ]; then
    # Increment counter and save error
    COUNT=0
    [ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$COUNTER_FILE"
    [ -n "$ERROR_MSG" ] && echo "$ERROR_MSG" > "$ERROR_FILE"

    if [ "$COUNT" -ge "$THRESHOLD" ]; then
        echo "1" > "/tmp/claude-tab-error-${PPID:-0}" 2>/dev/null || true

        # Collect recent errors for pattern analysis
        LAST_ERROR=""
        [ -f "$ERROR_FILE" ] && LAST_ERROR=$(cat "$ERROR_FILE" 2>/dev/null || echo "")

        echo "WARNING: $COUNT consecutive Bash command failures." >&2

        # Targeted correction based on error pattern
        if echo "$LAST_ERROR" | grep -qiE 'no such file|not found|no module'; then
            echo "DIAGNOSIS: Missing file or dependency. Check:" >&2
            echo "  - Does the file/directory exist? (ls the path)" >&2
            echo "  - Is the package installed? (uv pip list, brew list)" >&2
            echo "  - Are you in the right directory?" >&2
        elif echo "$LAST_ERROR" | grep -qiE 'permission denied|operation not permitted'; then
            echo "DIAGNOSIS: Permission issue." >&2
            echo "  - Check file permissions (ls -la)" >&2
            echo "  - Is the file read-only or locked?" >&2
            echo "  - Does the directory need different permissions?" >&2
        elif echo "$LAST_ERROR" | grep -qiE 'syntax error|unexpected token|parse error'; then
            echo "DIAGNOSIS: Syntax error in command or script." >&2
            echo "  - Write a .py or .sh file instead of inline commands" >&2
            echo "  - Check for quoting issues or missing escapes" >&2
            echo "  - Simplify: break the command into smaller steps" >&2
        elif echo "$LAST_ERROR" | grep -qiE 'connection refused|timeout|unreachable|dns'; then
            echo "DIAGNOSIS: Network issue." >&2
            echo "  - Is the service running? Check the port." >&2
            echo "  - Is there a firewall or proxy blocking?" >&2
            echo "  - Try a different endpoint or approach." >&2
        elif echo "$LAST_ERROR" | grep -qiE 'import|module|traceback'; then
            echo "DIAGNOSIS: Python import or runtime error." >&2
            echo "  - Use 'uv run python3' not bare 'python3'" >&2
            echo "  - Check if the package is in pyproject.toml" >&2
            echo "  - Read the full traceback before retrying" >&2
        else
            echo "DIAGNOSIS: Unclassified repeated failure." >&2
            echo "  - Last error: $LAST_ERROR" >&2
            echo "  - Try a fundamentally different approach" >&2
            echo "  - Or stop and ask the user for guidance" >&2
        fi

        # Log trigger for ROI analysis
        ~/Projects/skills/hooks/hook-trigger-log.sh "bash-failure-loop" "warn" "$COUNT failures: $LAST_ERROR" 2>/dev/null || true

        # Reset so the warning fires again after another THRESHOLD failures
        echo "0" > "$COUNTER_FILE"
    fi
else
    # Success — reset counter and clear error flag
    [ -f "$COUNTER_FILE" ] && echo "0" > "$COUNTER_FILE"
    echo "0" > "/tmp/claude-tab-error-${PPID:-0}" 2>/dev/null || true
fi

exit 0
