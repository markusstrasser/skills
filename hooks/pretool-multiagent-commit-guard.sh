#!/usr/bin/env bash
# pretool-multiagent-commit-guard.sh — Block git commit/add in main repo
# when multiple Claude agents are active. Forces worktree isolation.
#
# PreToolUse:Bash command hook.
# Replaces text-only CLAUDE.md rule that decayed to ~50% compliance.

INPUT=$(cat)

# Extract command from tool_input
CMD=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)

# Only check git commit/add commands
echo "$CMD" | grep -qE '^\s*git\s+(commit|add)\b' || exit 0

# Count claude processes
CLAUDE_PROCS=$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ')
[ "$CLAUDE_PROCS" -lt 2 ] && exit 0

# Check if in a worktree (git-common-dir differs from git-dir in worktrees)
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null)

if [ "$GIT_DIR" != "$GIT_COMMON" ]; then
    # In a worktree — safe
    exit 0
fi

# Block: main repo + multi-agent
~/Projects/skills/hooks/hook-trigger-log.sh "multiagent-commit" "block" \
    "procs=$CLAUDE_PROCS cmd=$(echo "$CMD" | head -c 60)" 2>/dev/null || true

echo '{"decision": "block", "reason": "MULTI-AGENT SAFETY: '"$CLAUDE_PROCS"' claude processes active in main repo (not a worktree). Risk: uncommitted changes from other agents get swept into your commit. Either: (1) use git add <specific-files> && git commit immediately after each edit, or (2) work in a worktree (isolation: worktree for subagents)."}'
exit 2
