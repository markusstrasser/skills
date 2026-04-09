#!/usr/bin/env bash
# pretool-multiagent-commit-guard.sh — Block git commit/add in main repo
# when multiple Claude agents are active. Forces worktree isolation.
#
# PreToolUse:Bash command hook.
# Replaces text-only CLAUDE.md rule that decayed to ~50% compliance.

INPUT=$(cat)

# Extract command from tool_input
CMD=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)

# Extract first line only — multi-line commit messages contain git substrings
# that would false-positive the grep patterns below.
CMD_FIRST=$(echo "$CMD" | head -1)

# Block dangerous git patterns that sweep in or destroy other agents' changes:
# - git add -A / --all / . — sweeps all changes
# - git add -p — interactive staging shows hunks from all agents' modifications
# - git checkout -- / git restore — destroys uncommitted changes
if echo "$CMD_FIRST" | grep -qE '^\s*git\s+add\s+(-A|--all|-p|--patch|\.\s*$|\.\s*&&)'; then
    : # dangerous add — continue to check
elif echo "$CMD_FIRST" | grep -qE '^\s*git\s+(checkout\s+--|restore\s)'; then
    : # destructive discard — continue to check
else
    exit 0  # git commit, specific-file add, or non-git command — all safe
fi

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

echo '{"decision": "block", "reason": "MULTI-AGENT SAFETY: '"$CLAUDE_PROCS"' claude processes active in main repo (not a worktree). Use git add <specific-files> (not -A/-p/.). For git checkout/restore: stash instead, or verify the files are yours."}'
exit 2
