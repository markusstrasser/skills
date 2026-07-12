#!/usr/bin/env bash
# pretool-multiagent-commit-guard.sh — Block git commit/add in main repo
# when multiple Claude agents are active. Forces worktree isolation.
#
# PreToolUse:Bash command hook.
# Replaces text-only CLAUDE.md rule that decayed to ~50% compliance.

INPUT=$(cat)

# Extract command and the command tool's actual working directory.
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
TOOL_DIR=$(printf '%s' "$INPUT" | jq -r \
    '.tool_input.workdir // .tool_input.cwd // .cwd // ""' 2>/dev/null)

# Extract first line only — multi-line commit messages contain git substrings
# that would false-positive the grep patterns below.
CMD_FIRST=$(echo "$CMD" | head -1)

resolve_target_dir() {
    local target_dir="${TOOL_DIR:-$PWD}"
    if [[ "$CMD_FIRST" =~ git[[:space:]]+-C[[:space:]]+([^[:space:]]+) ]]; then
        target_dir="${BASH_REMATCH[1]}"
        target_dir="${target_dir%\"}"
        target_dir="${target_dir#\"}"
        target_dir="${target_dir%\'}"
        target_dir="${target_dir#\'}"
    elif [[ "$CMD_FIRST" =~ (^|[[:space:]\;\&])cd[[:space:]]+([^[:space:]\;\&]+)[[:space:]]*\&\& ]]; then
        target_dir="${BASH_REMATCH[2]}"
    fi
    printf '%s\n' "$target_dir"
}

TARGET_DIR=$(resolve_target_dir)

# Block dangerous git patterns that sweep in or destroy other agents' changes:
# - git add -A / --all / . — sweeps all changes
# - git add -p — interactive staging shows hunks from all agents' modifications
# - git checkout -- / git restore — destroys uncommitted changes
# - git commit (bare, no --only / --amend / -i) — sweeps pre-staged files from
#   other agents into this commit. The 2026-05-27 substrate session lost
#   correct provenance on commit 486973e because Phase 1's agent ran bare
#   `git commit` while Phase 5's files were already staged.
if echo "$CMD_FIRST" | grep -qE '^[[:space:]]*git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?add[[:space:]]+(-A|--all|-p|--patch|\.[[:space:]]*$|\.[[:space:]]*&&)'; then
    : # dangerous add — continue to check
elif echo "$CMD_FIRST" | grep -qE '^[[:space:]]*git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?(checkout[[:space:]]+--|restore[[:space:]])'; then
    : # destructive discard — continue to check
elif echo "$CMD_FIRST" | grep -qE '^[[:space:]]*git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?commit([[:space:]]|$)'; then
    # Allow safe forms that scope the commit explicitly:
    #   --only <paths>, --include <paths>, --amend, -i (interactive), -p (patch)
    # Bare `git commit` (no path scope) is dangerous in multi-agent mode.
    if echo "$CMD_FIRST" | grep -qE '[[:space:]](--only|--include|-o|--amend|-i|--interactive|-p|--patch)([[:space:]]|$)'; then
        exit 0  # explicitly scoped — safe
    fi
    # Merge in progress: git FORBIDS --only ("cannot do a partial commit during a merge"),
    # and `git merge --continue` commits the identical index and was never blocked — so
    # blocking bare commit here adds friction, not safety (2026-07-10 p23-fixer merge).
    # The agent still owes a staged-set review (git status) before committing a merge.
    if git -C "$TARGET_DIR" rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
        ~/Projects/skills/hooks/hook-trigger-log.sh "multiagent-commit" "allow-merge" \
            "MERGE_HEAD present; --only impossible during merge" 2>/dev/null || true
        exit 0
    fi
    : # bare commit — continue to multi-agent check
else
    exit 0  # specific-file add, log/diff/status, or non-git command — all safe
fi

# Check the command TARGET, not the hook/session cwd. Absolute paths avoid
# comparing `.git` with an equivalent absolute common-dir spelling.
TARGET_ROOT=$(git -C "$TARGET_DIR" rev-parse --show-toplevel 2>/dev/null || true)
GIT_DIR=$(git -C "$TARGET_ROOT" rev-parse --path-format=absolute --git-dir 2>/dev/null || true)
GIT_COMMON=$(git -C "$TARGET_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)

if [ -n "$GIT_DIR" ] && [ -n "$GIT_COMMON" ] && [ "$GIT_DIR" != "$GIT_COMMON" ]; then
    # In a worktree — safe
    exit 0
fi

# Single-source the same checkout-scoped peer detector used by SessionStart and
# Stop. Global process counts confuse agents in unrelated repositories with
# writers sharing this index, producing false commit blocks.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PEER_SESSION_COUNT_BIN="${PEER_SESSION_COUNT_BIN:-$HOOK_DIR/peer-session-count.sh}"
PEER_COUNT=$("$PEER_SESSION_COUNT_BIN" "$TARGET_ROOT" 2>/dev/null || echo 0)
[[ "$PEER_COUNT" =~ ^[0-9]+$ ]] || PEER_COUNT=0
[ "$PEER_COUNT" -lt 1 ] && exit 0

# Block: a real peer shares this main checkout.
~/Projects/skills/hooks/hook-trigger-log.sh "multiagent-commit" "block" \
    "repo_peers=$PEER_COUNT target_class=shared/main target_root=$TARGET_ROOT cmd=$(echo "$CMD" | head -c 60)" 2>/dev/null || true

echo '{"decision": "block", "reason": "MULTI-AGENT SAFETY: '"$PEER_COUNT"' peer Claude session(s) share this repository checkout. Git target classification: shared/main checkout (not a linked worktree). For git add: use specific files (not -A/-p/.). For git commit: pass --only <files> (or --amend) so a parallel agent'\''s pre-staged files do not sweep into this commit (2026-05-27 substrate-session sweep on 486973e). For git checkout/restore (destructive): prefer Read + Edit to repair in place; if you must discard, run \"git stash push -- <files>\" first so it'\''s reversible. Completing a merge? bare commit is ALLOWED when MERGE_HEAD exists (git forbids --only there) — review git status first."}'
exit 2
