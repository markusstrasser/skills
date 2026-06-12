#!/usr/bin/env bash
# pretool-multiagent-commit-guard.sh — Block git commit/add in main repo
# when multiple Claude agents are active. Forces worktree isolation.
#
# PreToolUse:Bash command hook.
# Replaces text-only CLAUDE.md rule that decayed to ~50% compliance.

INPUT=$(cat)

# Extract command from tool_input
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)

# Extract first line only — multi-line commit messages contain git substrings
# that would false-positive the grep patterns below.
CMD_FIRST=$(echo "$CMD" | head -1)

# Block dangerous git patterns that sweep in or destroy other agents' changes:
# - git add -A / --all / . — sweeps all changes
# - git add -p — interactive staging shows hunks from all agents' modifications
# - git checkout -- / git restore — destroys uncommitted changes
# - git commit (bare, no --only / --amend / -i) — sweeps pre-staged files from
#   other agents into this commit. The 2026-05-27 substrate session lost
#   correct provenance on commit 486973e because Phase 1's agent ran bare
#   `git commit` while Phase 5's files were already staged.
if echo "$CMD_FIRST" | grep -qE '^\s*git\s+add\s+(-A|--all|-p|--patch|\.\s*$|\.\s*&&)'; then
    : # dangerous add — continue to check
elif echo "$CMD_FIRST" | grep -qE '^\s*git\s+(checkout\s+--|restore\s)'; then
    : # destructive discard — continue to check
elif echo "$CMD_FIRST" | grep -qE '^\s*git\s+(-C\s+\S+\s+)?commit\b'; then
    # Allow safe forms that scope the commit explicitly:
    #   --only <paths>, --include <paths>, --amend, -i (interactive), -p (patch)
    # Bare `git commit` (no path scope) is dangerous in multi-agent mode.
    if echo "$CMD" | grep -qE '\s(--only|--include|-o|--amend|-i|--interactive|-p|--patch)\b'; then
        exit 0  # explicitly scoped — safe
    fi
    : # bare commit — continue to multi-agent check
else
    exit 0  # specific-file add, log/diff/status, or non-git command — all safe
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

echo '{"decision": "block", "reason": "MULTI-AGENT SAFETY: '"$CLAUDE_PROCS"' claude processes active in main repo (not a worktree). For git add: use specific files (not -A/-p/.). For git commit: pass --only <files> (or --amend) so a parallel agent'\''s pre-staged files do not sweep into this commit (2026-05-27 substrate-session sweep on 486973e). For git checkout/restore (destructive): prefer Read + Edit to repair in place; if you must discard, run \"git stash push -- <files>\" first so it'\''s reversible."}'
exit 2
