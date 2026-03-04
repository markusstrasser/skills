#!/usr/bin/env bash
# permission-auto-allow.sh — PermissionRequest hook.
# Auto-approves known-safe read-only tools to reduce permission fatigue.
# Deployed disabled (not in settings.json) until hook telemetry confirms
# permission prompt frequency justifies it. Constitution principle #3.
#
# Exit 0 with JSON {"hookSpecificOutput":{"hookEventName":"PermissionRequest",
#   "decision":{"behavior":"allow"}}} to auto-allow.
# Exit 0 with no output to fall through to normal permission prompt.

trap 'exit 0' ERR

INPUT=$(cat)

TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null) || exit 0

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

allow_tool() {
    "$HOOK_DIR/hook-trigger-log.sh" "permission-auto-allow" "allow" "$1" 2>/dev/null || true
    echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
    exit 0
}

case "$TOOL" in
    Read|Glob|Grep|WebSearch|WebFetch)
        allow_tool "$TOOL"
        ;;
    mcp__context7__*|mcp__research__search_papers|mcp__research__list_*|mcp__research__get_*)
        allow_tool "$TOOL"
        ;;
    mcp__brave-search__*|mcp__perplexity__*|mcp__paper-search__search_*|mcp__meta-knowledge__*)
        allow_tool "$TOOL"
        ;;
    Bash)
        CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null) || exit 0
        case "$CMD" in
            git\ log*|git\ diff*|git\ status*|git\ branch*|git\ show*|ls*|wc\ *|pwd|date|which\ *)
                allow_tool "Bash:${CMD:0:50}"
                ;;
        esac
        ;;
esac

# All other tools — fall through to normal permission prompt
exit 0
