#!/usr/bin/env bash
# posttool-failure-log.sh — PostToolUseFailure hook.
# Logs all tool failures (any tool, not just Bash) with error classification.
# Writes to ~/.claude/tool-failures.jsonl + calls hook-trigger-log.sh.
# Always exits 0 (PostToolUseFailure can't block — tool already failed).

LOG_FILE="$HOME/.claude/tool-failures.jsonl"
HOOK_DIR="$(dirname "$0")"

INPUT=$(cat)

# Extract fields via Python (robust JSON parsing).
# Field name by event (verified vs live CC hooks docs 2026-05-30):
#   PostToolUseFailure -> top-level "error" (string)         <- this hook's wiring
#   PostToolUse        -> "tool_response" (object or string)
# The legacy "tool_result" key does NOT exist in either payload — reading it
# discarded 100% of error text for >=14d. Read all three, error-first.
eval "$(echo "$INPUT" | python3 -c '
import sys, json, shlex
try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "unknown")
    # 1) PostToolUseFailure: top-level "error" string
    err = data.get("error") or ""
    # 2) Fallback: PostToolUse "tool_response" (obj or str), then legacy keys
    if not err:
        tr = data.get("tool_response") or data.get("tool_result") or data.get("output") or ""
        if isinstance(tr, dict):
            err = tr.get("stderr") or tr.get("error") or tr.get("message") or ""
            if not err and tr.get("is_error"):
                err = json.dumps(tr)[:300]
        elif isinstance(tr, list):
            err = json.dumps(tr)[:300]
        else:
            err = str(tr)
    err = str(err or "").strip()[:300]
    is_interrupt = bool(data.get("is_interrupt", False))
    inp = data.get("tool_input", {})
    # Build input summary: file_path for file tools, command for Bash, pattern for search
    summary = ""
    if isinstance(inp, dict):
        summary = inp.get("file_path", "") or inp.get("command", "")[:120] or inp.get("pattern", "") or inp.get("query", "")[:120] or ""
    print(f"TOOL={shlex.quote(tool)}")
    print(f"ERROR_MSG={shlex.quote(err)}")
    print(f"INPUT_SUMMARY={shlex.quote(str(summary)[:120])}")
    print(f"IS_INTERRUPT={shlex.quote(str(is_interrupt).lower())}")
except Exception:
    print("TOOL=unknown")
    print("ERROR_MSG=parse_failure")
    print("INPUT_SUMMARY=")
    print("IS_INTERRUPT=false")
' 2>/dev/null)"

# Classify error
classify_error() {
    local msg="$1"
    case "$msg" in
        *"does not exist"*|*"No such file"*|*"not found"*|*"ENOENT"*)
            echo "missing_file" ;;
        *"permission"*|*"Permission denied"*|*"EACCES"*)
            echo "permission" ;;
        *"syntax"*|*"SyntaxError"*|*"parse error"*|*"invalid"*)
            echo "syntax" ;;
        *"timeout"*|*"timed out"*|*"ETIMEDOUT"*)
            echo "timeout" ;;
        *"network"*|*"connect"*|*"ECONNREFUSED"*|*"DNS"*)
            echo "network" ;;
        *"rate limit"*|*"429"*|*"Too Many"*)
            echo "rate_limit" ;;
        *"mcp"*|*"MCP"*|*"server"*)
            echo "mcp_error" ;;
        *"not unique"*|*"unique"*)
            echo "edit_not_unique" ;;
        *)
            echo "other" ;;
    esac
}

# User interrupts are not real errors — classify them out so they don't pollute
# the error corpus (PostToolUseFailure fires on Ctrl-C / interrupt too).
if [ "${IS_INTERRUPT:-false}" = "true" ]; then
    ERROR_CLASS="interrupt"
else
    ERROR_CLASS=$(classify_error "$ERROR_MSG")
fi
PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PROJECT=$(basename "$PROJECT")
SESSION="${CLAUDE_SESSION_ID:-unknown}"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log to tool-failures.jsonl (use python for correct JSON escaping of error text)
ERROR_MSG="$ERROR_MSG" INPUT_SUMMARY="$INPUT_SUMMARY" TOOL="$TOOL" \
ERROR_CLASS="$ERROR_CLASS" PROJECT="$PROJECT" SESSION="$SESSION" TS="$TS" \
IS_INTERRUPT="${IS_INTERRUPT:-false}" python3 -c '
import os, json
rec = {
    "ts": os.environ["TS"], "tool": os.environ["TOOL"],
    "error_class": os.environ["ERROR_CLASS"], "error_msg": os.environ["ERROR_MSG"],
    "input_summary": os.environ["INPUT_SUMMARY"], "project": os.environ["PROJECT"],
    "session": os.environ["SESSION"], "is_interrupt": os.environ["IS_INTERRUPT"] == "true",
}
with open(os.path.expanduser("~/.claude/tool-failures.jsonl"), "a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
' 2>/dev/null

# Also log to unified hook telemetry
"$HOOK_DIR/hook-trigger-log.sh" "tool-failure" "log" "$ERROR_CLASS: ${TOOL}" 2>/dev/null || true

exit 0
