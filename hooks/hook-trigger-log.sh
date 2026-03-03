#!/usr/bin/env bash
# hook-trigger-log.sh — Log hook triggers to JSONL for ROI analysis.
# Called by decision-making hooks when they fire (warn or block).
#
# Usage: source this or call directly:
#   echo '{"hook":"search-burst","action":"block","count":8}' | ~/Projects/skills/hooks/hook-trigger-log.sh
# Or from another hook:
#   log_hook_trigger "bash-failure-loop" "warn" "5 consecutive failures"
#
# Env: HOOK_TRIGGER_LOG (default: ~/.claude/hook-triggers.jsonl)

LOG_FILE="${HOOK_TRIGGER_LOG:-$HOME/.claude/hook-triggers.jsonl}"

# If called with args: hook_name, action, detail
if [ $# -ge 2 ]; then
    HOOK_NAME="$1"
    ACTION="$2"  # warn, block, allow, remind
    DETAIL="${3:-}"
    PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    PROJECT=$(basename "$PROJECT")
    SESSION="${CLAUDE_SESSION_ID:-unknown}"
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf '{"ts":"%s","hook":"%s","action":"%s","detail":"%s","project":"%s","session":"%s","tool":"%s"}\n' \
        "$TS" "$HOOK_NAME" "$ACTION" "$DETAIL" "$PROJECT" "$SESSION" "${CLAUDE_TOOL_NAME:-}" >> "$LOG_FILE" 2>/dev/null
    exit 0
fi

# If called via pipe (stdin JSON)
INPUT=$(cat)
if [ -n "$INPUT" ]; then
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    PROJECT=$(basename "$PROJECT")
    # Merge timestamp and project into the JSON
    echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    data['ts'] = '$TS'
    data['project'] = '$PROJECT'
    data['session'] = '${CLAUDE_SESSION_ID:-unknown}'
    print(json.dumps(data))
except:
    pass
" >> "$LOG_FILE" 2>/dev/null
fi
exit 0
