#!/usr/bin/env bash
# permission-denied-retry.sh — PermissionDenied hook (v2.1.89+).
# Returns {"retry": true} for known-safe tool calls that the auto-mode
# classifier incorrectly denied. The retry surfaces the normal permission
# prompt instead of silently dropping the action.
#
# Safe retry patterns:
#   - Write/Edit to .claude/plans/, .claude/checkpoint.md, .claude/rules/
#   - Write/Edit to memory dirs (~/.claude/projects/*/memory/)
#   - ExitPlanMode, EnterPlanMode (always safe)
#   - TaskCreate, TaskUpdate, TaskGet, TaskList (always safe)
#
# Non-retriable (let the denial stand):
#   - Bash commands (could be destructive)
#   - Write/Edit to protected files (CLAUDE.md, GOALS.md, etc.)
#   - Unknown tools

trap 'exit 0' ERR

INPUT=$(cat)

TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null) || exit 0

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

retry_tool() {
    "$HOOK_DIR/hook-trigger-log.sh" "permission-denied-retry" "retry" "$1" 2>/dev/null || true
    echo '{"retry": true}'
    exit 0
}

# Tools that are always safe to retry
case "$TOOL" in
    ExitPlanMode|EnterPlanMode|ExitWorktree|EnterWorktree)
        retry_tool "$TOOL"
        ;;
    TaskCreate|TaskUpdate|TaskGet|TaskList|TaskOutput|TaskStop)
        retry_tool "$TOOL"
        ;;
    SendMessage)
        retry_tool "$TOOL"
        ;;
esac

# Write/Edit — retry only for safe paths
if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
    FPATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null) || exit 0

    case "$FPATH" in
        */.claude/plans/*)
            retry_tool "$TOOL:plans"
            ;;
        */.claude/checkpoint.md)
            retry_tool "$TOOL:checkpoint"
            ;;
        */.claude/rules/*)
            retry_tool "$TOOL:rules"
            ;;
        */memory/*.md)
            retry_tool "$TOOL:memory"
            ;;
        */.scratch/*)
            retry_tool "$TOOL:scratch"
            ;;
        */artifacts/*)
            retry_tool "$TOOL:artifacts"
            ;;
    esac
fi

# All other denials — let them stand
exit 0
