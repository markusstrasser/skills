#!/usr/bin/env bash
# posttool-bash-failure-loop.sh — Detect consecutive Bash failures with targeted correction.
# Wired on BOTH events (matcher Bash):
#   PostToolUseFailure — a failed call (non-zero exit); error text in top-level "error".
#   PostToolUse        — a successful call; resets the counter. Codex has no failure
#                        event, so a tool_response carrying a non-zero exit code counts too.
# Before 2026-10-24 this hook sat on PostToolUse only and read top-level exitCode/stderr,
# fields Claude never sends: it fired once ever (a test), leaving the constitution's
# ">5 failure loop" rule unenforced. After THRESHOLD failures it injects a diagnosis.
# Based on AgentDebug finding: targeted correction +24% over blind retry.
# Fails open: if this script errors, exit 0.

trap 'exit 0' ERR

THRESHOLD=5

INPUT=$(cat)

# One counter per calling agent (in-process subagents share the CLI's PID, so a $PPID-only
# counter chained one sibling's failures onto another's and let any sibling's success reset it).
. "$(dirname "$0")/lib_hook_identity.sh" 2>/dev/null || exit 0
hook_identity "$INPUT"
COUNTER_FILE="/tmp/claude-bash-failure-count-${HOOK_OWNER}"
ERROR_FILE="/tmp/claude-bash-last-error-${HOOK_OWNER}"

RESULT=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    event = d.get("hook_event_name", "")
    if d.get("is_interrupt"):
        print("skip|")  # the user stopped it; not a failure loop
    elif event == "PostToolUseFailure":
        err = str(d.get("error") or "")
        lines = [l.strip() for l in err.splitlines() if l.strip()]
        keys = ("error", "failed", "denied", "not found", "no such", "cannot", "traceback")
        hit = next((l for l in lines if any(k in l.lower() for k in keys)), lines[-1] if lines else "")
        print("fail|" + hit[:200])
    else:
        tr = d.get("tool_response")
        code = 0
        if isinstance(tr, dict):
            code = tr.get("exit_code", tr.get("exitCode", 0)) or 0
        if code:
            err = str(tr.get("stderr") or tr.get("stdout") or "").strip().splitlines()
            print("fail|" + (err[-1][:200] if err else f"exit {code}"))
        else:
            print("ok|")
except Exception:
    print("skip|")
' 2>/dev/null)

STATUS="${RESULT%%|*}"
ERROR_MSG="${RESULT#*|}"

if [ "$STATUS" = "fail" ]; then
    COUNT=0
    [ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$COUNTER_FILE"
    [ -n "$ERROR_MSG" ] && echo "$ERROR_MSG" > "$ERROR_FILE"

    if [ "$COUNT" -ge "$THRESHOLD" ]; then
        echo "1" > "/tmp/claude-tab-error-${PPID:-0}" 2>/dev/null || true

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
        MSG="BASH FAILURE LOOP: $COUNT consecutive failures. $DIAGNOSIS"

        ~/Projects/skills/hooks/hook-trigger-log.sh "bash-failure-loop" "block" "$COUNT failures: $LAST_ERROR" 2>/dev/null || true

        # Reset so the diagnosis fires again after another THRESHOLD failures
        echo "0" > "$COUNTER_FILE"

        # The call already ran: deliver the diagnosis in-turn as additionalContext.
        EVENT=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("hook_event_name") or "PostToolUse")' 2>/dev/null || echo PostToolUse)
        MSG="$MSG" EVENT="$EVENT" python3 -c 'import json,os; print(json.dumps({"hookSpecificOutput": {"hookEventName": os.environ["EVENT"], "additionalContext": os.environ["MSG"]}}))'
    fi
elif [ "$STATUS" = "ok" ]; then
    [ -f "$COUNTER_FILE" ] && echo "0" > "$COUNTER_FILE"
    echo "0" > "/tmp/claude-tab-error-${PPID:-0}" 2>/dev/null || true
fi

exit 0
