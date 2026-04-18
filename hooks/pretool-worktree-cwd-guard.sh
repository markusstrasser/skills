#!/usr/bin/env bash
# pretool-worktree-cwd-guard.sh — Warn when subagents in a worktree run python/
# pytest/uv/modal commands without chaining `cd $WORKTREE_PATH`. ADVISORY-ONLY.
#
# Triggered: PreToolUse:Bash globally.
# Activates only when WORKTREE_PATH env is set (subagent context).
# Rationale: Bash sessions don't persist CWD across separate tool calls.
# Subagents in worktrees that don't chain `cd` execute against main repo.
# Source: improvement-log 2026-04-17 M001 (genomics 54b4a4fe).

set -uo pipefail

[ -z "${WORKTREE_PATH:-}" ] && exit 0

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command","")[:500])' 2>/dev/null || echo "")
[ -z "$COMMAND" ] && exit 0

# Match: command starts with uv|python3|pytest|modal — and does NOT chain `cd $WORKTREE_PATH` first
if echo "$COMMAND" | grep -qE '^[[:space:]]*(uv[[:space:]]+run|python3?[[:space:]]|pytest|modal[[:space:]]+(run|deploy))'; then
    if ! echo "$COMMAND" | grep -qE "cd[[:space:]]+(\\\$WORKTREE_PATH|\"?${WORKTREE_PATH//\//\\/})"; then
        echo "ADVISORY: subagent bash command will run from main repo CWD, not worktree." >&2
        echo "Worktree: $WORKTREE_PATH" >&2
        echo "Chain explicitly: cd \$WORKTREE_PATH && <your command>" >&2
        echo "(Bash sessions reset CWD between tool calls.)" >&2
        ~/Projects/skills/hooks/hook-trigger-log.sh "worktree-cwd-guard" "warn" "wt=$(basename $WORKTREE_PATH) cmd=$(echo "$COMMAND" | head -c 60)" 2>/dev/null || true
    fi
fi
exit 0
