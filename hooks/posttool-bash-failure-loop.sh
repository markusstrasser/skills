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

        # Targeted correction based on error pattern
        DIAGNOSIS=""
        if echo "$LAST_ERROR" | grep -qiE 'no such file|not found|no module'; then
            DIAGNOSIS="Missing file or dependency. Check: does the file/directory exist? Is the package installed (uv pip list)? Are you in the right directory?"
        elif echo "$LAST_ERROR" | grep -qiE 'permission denied|operation not permitted'; then
            DIAGNOSIS="Permission issue. Check file permissions (ls -la). Is the file read-only or locked?"
        elif echo "$LAST_ERROR" | grep -qiE 'syntax error|unexpected token|parse error'; then
            DIAGNOSIS="Syntax error. Write a .py or .sh file instead of inline commands. Check quoting and escapes."
        elif echo "$LAST_ERROR" | grep -qiE 'connection refused|timeout|unreachable|dns'; then
            DIAGNOSIS="Network issue. Is the service running? Check the port. Try a different endpoint."
        elif echo "$LAST_ERROR" | grep -qiE 'import|module|traceback'; then
            DIAGNOSIS="Python import/runtime error. Use 'uv run python3' not bare 'python3'. Check pyproject.toml."
        else
            DIAGNOSIS="Unclassified repeated failure. Last error: ${LAST_ERROR:0:120}. Try a fundamentally different approach or ask the user."
        fi

        # Output JSON to stdout so agent actually sees the warning
        MSG="BASH FAILURE LOOP: $COUNT consecutive failures. $DIAGNOSIS"
        SAFE_MSG=$(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
        echo "{\"additionalContext\": ${SAFE_MSG}}"

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
