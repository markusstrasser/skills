#!/usr/bin/env bash
# pretool-genomics-mcp-routing.sh — advisory routing toward genomics MCP tools
# for common Modal and JSON shell workflows.

trap 'exit 0' ERR

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null) || exit 0
[ -n "$CMD" ] || exit 0

SESSION_ID=""
for SID_PATH in ".claude/current-session-id" "$HOME/.claude/current-session-id"; do
    if [ -f "$SID_PATH" ]; then
        SESSION_ID=$(tr -d "[:space:]" < "$SID_PATH" 2>/dev/null)
        [ -n "$SESSION_ID" ] && break
    fi
done

TRACKER="/tmp/claude-genomics-mcp-routing-${SESSION_ID:-$PPID}.txt"

seen() {
    local key="$1"
    [ -f "$TRACKER" ] && grep -qxF "$key" "$TRACKER" 2>/dev/null
}

remember() {
    local key="$1"
    touch "$TRACKER"
    grep -qxF "$key" "$TRACKER" 2>/dev/null || printf '%s\n' "$key" >> "$TRACKER"
}

MESSAGES=()
TRIGGERED=()

if echo "$CMD" | grep -qE '(^|[[:space:]])modal[[:space:]]+app[[:space:]]+logs([[:space:]]|$)' && ! seen "modal-logs"; then
    remember "modal-logs"
    MESSAGES+=('Use `mcp__genomics__modal_logs_tail` for detached Modal app logs instead of `modal app logs`; it gives bounded reads without a hanging tail.')
    TRIGGERED+=("modal-logs")
fi

if echo "$CMD" | grep -qE '(^|[[:space:]])modal[[:space:]]+volume[[:space:]]+(ls|get|list|cat)([[:space:]]|$)' && ! seen "modal-volume"; then
    remember "modal-volume"
    MESSAGES+=('Use `mcp__genomics__modal_volume_inspect` when you only need to inspect volume files or `_STATUS.json`; it replaces `modal volume get/ls` plus local cleanup.')
    TRIGGERED+=("modal-volume")
fi

if echo "$CMD" | grep -q '\.json' && echo "$CMD" | grep -qE '(^|[[:space:]])(jq|cat|sed|head|tail|python|python3)([[:space:]]|$)' && ! seen "json-query"; then
    remember "json-query"
    MESSAGES+=('Use `mcp__genomics__query_json` for pipeline JSON inspection instead of ad hoc shell parsing; it can navigate, filter, project, and group in one call.')
    TRIGGERED+=("json-query")
fi

[ "${#MESSAGES[@]}" -gt 0 ] || exit 0

~/Projects/skills/hooks/hook-trigger-log.sh "genomics-mcp-routing" "remind" "$(IFS=,; echo "${TRIGGERED[*]}")" 2>/dev/null || true

CONTEXT=$(printf '%s\n' "${MESSAGES[@]}" | python3 -c '
import json, sys
lines = [line.strip() for line in sys.stdin if line.strip()]
text = "Genomics MCP routing:\n- " + "\n- ".join(lines)
print(json.dumps(text))
')

printf '{"additionalContext":%s}\n' "$CONTEXT"

exit 0
