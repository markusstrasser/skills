#!/usr/bin/env bash
# posttool-failure-log.sh — PostToolUseFailure hook.
# Logs all tool failures (any tool, not just Bash) with error classification.
# Writes to ~/.claude/tool-failures.jsonl + calls hook-trigger-log.sh.
# Always exits 0 (PostToolUseFailure can't block — tool already failed).

LOG_FILE="$HOME/.claude/tool-failures.jsonl"
HOOK_DIR="$(dirname "$0")"

INPUT=$(cat)

# Extract fields via Python (robust JSON parsing)
eval "$(echo "$INPUT" | python3 -c '
import sys, json, shlex
try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "unknown")
    result = str(data.get("tool_result", ""))[:200]
    inp = data.get("tool_input", {})
    # Build input summary: file_path for file tools, command for Bash, pattern for search
    summary = ""
    if isinstance(inp, dict):
        summary = inp.get("file_path", "") or inp.get("command", "")[:100] or inp.get("pattern", "") or inp.get("query", "")[:100] or ""
    print(f"TOOL={shlex.quote(tool)}")
    print(f"ERROR_MSG={shlex.quote(result[:200])}")
    print(f"INPUT_SUMMARY={shlex.quote(str(summary)[:100])}")
except Exception:
    print("TOOL=unknown")
    print("ERROR_MSG=parse_failure")
    print("INPUT_SUMMARY=")
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

ERROR_CLASS=$(classify_error "$ERROR_MSG")
PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PROJECT=$(basename "$PROJECT")
SESSION="${CLAUDE_SESSION_ID:-unknown}"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log to tool-failures.jsonl
printf '{"ts":"%s","tool":"%s","error_class":"%s","error_msg":"%s","input_summary":"%s","project":"%s","session":"%s"}\n' \
    "$TS" "$TOOL" "$ERROR_CLASS" "${ERROR_MSG//\"/\\\"}" "${INPUT_SUMMARY//\"/\\\"}" "$PROJECT" "$SESSION" >> "$LOG_FILE" 2>/dev/null

# Also log to unified hook telemetry
"$HOOK_DIR/hook-trigger-log.sh" "tool-failure" "log" "$ERROR_CLASS: ${TOOL}" 2>/dev/null || true

exit 0
