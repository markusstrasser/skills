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

# Hoisted (was defined just before the final peer check, below) — the T3
# exposure probe (guard-forcerate-study / rescue-class-surface-closure-loop,
# arc-agi loop/backlog.jsonl rows 906/909: "git commit --only when peers
# exist = eligible-and-clean for the commit guard") needs peer detection on
# an EARLIER branch than the original block check.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PEER_SESSION_COUNT_BIN="${PEER_SESSION_COUNT_BIN:-$HOOK_DIR/peer-session-count.sh}"

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

# Trailing `-- <paths>` pathspec, git-semantically IDENTICAL to --only (a
# pathspec given to `git commit` with no --only/-i already defaults to
# --only's "working-tree content of just these paths" behavior -- verified
# via `git help commit` and empirically 2026-07-18). This is the canonical
# form taught in teammate-dispatch-protocol.md / CLAUDE.md git_rules
# (2026-07-18 "pathspec the COMMIT" entry): `git commit -m "..." -- <paths>`.
# Recognizing it here fixes a false-positive: before this, ONLY the literal
# --only/--include/-i/-p/--amend flags were allow-listed, so the exact form
# agents are told to use was needlessly blocked whenever peers were present
# ("Do not hard-block pathspec'd commits (too noisy)" -- 2026-07-18).
#
# Token-aware (shlex), not a naive substring/regex match on CMD_FIRST, for
# two reasons: (1) the pathspec is the LAST thing on the command line, and a
# multi-line commit message (`-m "Subject\n\nBody"`) pushes it past line 1,
# invisible to every CMD_FIRST-only check elsewhere in this file; (2) a
# regex anchored on a literal `--` token nearly shipped with a live false
# positive -- this repos own commit convention documents a `Rejected: ...`
# trailer, and an agent typing `Rejected: -- old approach` as the LAST body
# line (using `--` instead of the convention's em-dash) would make a bare,
# genuinely-unscoped commit look "pathspec'd" to a naive end-of-string
# regex. shlex.split() respects quote boundaries, so that entire message is
# ONE token, not a real `--` separator -- verified against both cases (and
# 13 others) before this landed. -a/--all is excluded even with a trailing
# pathspec (git itself rejects the combination -- "paths ... with -a does
# not make sense" -- but this check should not advertise it as safe
# either); a bare `.` pathspec is excluded too (sweeps the whole cwd, same
# hazard class as `git add .`).
_pathspec_commit_is_safe() {
    printf '%s' "$1" | python3 -c '
import shlex, sys
cmd = sys.stdin.read()
try:
    tokens = shlex.split(cmd)
except ValueError:
    sys.exit(1)
if any(t in ("-a", "--all") for t in tokens):
    sys.exit(1)
if "--" not in tokens:
    sys.exit(1)
idx = len(tokens) - 1 - tokens[::-1].index("--")
trailing = tokens[idx + 1:]
if not trailing:
    sys.exit(1)
if any(t == "." or t.startswith("-") for t in trailing):
    sys.exit(1)
sys.exit(0)
' 2>/dev/null
}

# Block dangerous git patterns that sweep in or destroy other agents' changes:
# - git add -A / --all / . — sweeps all changes
# - git add -p — interactive staging shows hunks from all agents' modifications
# - git checkout -- / git restore — destroys uncommitted changes
# - git commit (bare, no --only / --amend / -i / trailing pathspec) — sweeps
#   pre-staged files from other agents into this commit. The 2026-05-27
#   substrate session lost correct provenance on commit 486973e because
#   Phase 1's agent ran bare `git commit` while Phase 5's files were already
#   staged.
if echo "$CMD_FIRST" | grep -qE '^[[:space:]]*git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?add[[:space:]]+(-A|--all|-p|--patch|\.[[:space:]]*$|\.[[:space:]]*&&)'; then
    : # dangerous add — continue to check
elif echo "$CMD_FIRST" | grep -qE '^[[:space:]]*git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?(checkout[[:space:]]+--|restore[[:space:]])'; then
    : # destructive discard — continue to check
elif echo "$CMD_FIRST" | grep -qE '^[[:space:]]*git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?commit([[:space:]]|$)'; then
    # Allow safe forms that scope the commit explicitly:
    #   --only <paths>, --include <paths>, --amend, -i (interactive), -p (patch),
    #   or a trailing `-- <paths>` pathspec (git-semantically == --only, see
    #   _pathspec_commit_is_safe above).
    # Bare `git commit` (no path scope at all) is dangerous in multi-agent mode.
    if echo "$CMD_FIRST" | grep -qE '[[:space:]](--only|--include|-o|--amend|-i|--interactive|-p|--patch)([[:space:]]|$)' \
       || _pathspec_commit_is_safe "$CMD"; then
        # T3 exposure probe: this guard's precondition (a git-commit call in
        # a shared/main checkout with a peer present) matched, but the
        # command was ALREADY safe — log the eligible-and-clean row the
        # rescues-per-100-eligible-exposures denominator needs. Bounded to
        # this already-narrow git-commit branch (not every git call), same
        # cost class as the block-path peer check below. Fires identically
        # for the flag-based (--only/etc.) and trailing-pathspec forms —
        # both are the same "already safe" event class for this study.
        _T3_ROOT=$(git -C "$TARGET_DIR" rev-parse --show-toplevel 2>/dev/null || true)
        if [ -n "$_T3_ROOT" ]; then
            _T3_GD=$(git -C "$_T3_ROOT" rev-parse --path-format=absolute --git-dir 2>/dev/null || true)
            _T3_GC=$(git -C "$_T3_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
            if [ -n "$_T3_GD" ] && [ "$_T3_GD" = "$_T3_GC" ]; then
                # shared/main checkout, not a linked worktree — the guard's
                # precondition can actually apply here; check peers.
                _T3_PC=$("$PEER_SESSION_COUNT_BIN" "$_T3_ROOT" 2>/dev/null || echo 0)
                [[ "$_T3_PC" =~ ^[0-9]+$ ]] || _T3_PC=0
                if [ "$_T3_PC" -ge 1 ]; then
                    "$HOOK_DIR/hook-trigger-log.sh" "multiagent-commit" "exposure-clean" \
                        "peers=$_T3_PC target_class=shared/main" "$CMD" 2>/dev/null || true
                fi
            fi
        fi
        exit 0  # explicitly scoped — safe
    fi
    # Merge in progress: git FORBIDS --only ("cannot do a partial commit during a merge"),
    # and `git merge --continue` commits the identical index and was never blocked — so
    # blocking bare commit here adds friction, not safety (2026-07-10 p23-fixer merge).
    # The agent still owes a staged-set review (git status) before committing a merge.
    if git -C "$TARGET_DIR" rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
        "$HOOK_DIR/hook-trigger-log.sh" "multiagent-commit" "allow-merge" \
            "MERGE_HEAD present; --only impossible during merge" "$CMD" 2>/dev/null || true
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
# writers sharing this index, producing false commit blocks. (HOOK_DIR /
# PEER_SESSION_COUNT_BIN are hoisted near the top now — the T3 exposure probe
# on the safe --only branch above needs them earlier too.)
PEER_COUNT=$("$PEER_SESSION_COUNT_BIN" "$TARGET_ROOT" 2>/dev/null || echo 0)
[[ "$PEER_COUNT" =~ ^[0-9]+$ ]] || PEER_COUNT=0
[ "$PEER_COUNT" -lt 1 ] && exit 0

# Block: a real peer shares this main checkout.
"$HOOK_DIR/hook-trigger-log.sh" "multiagent-commit" "block" \
    "repo_peers=$PEER_COUNT target_class=shared/main target_root=$TARGET_ROOT cmd=$(echo "$CMD" | head -c 60)" "$CMD" 2>/dev/null || true

# Built via jq --arg (not a hand-escaped single-quoted JSON literal) so the
# guidance text below can use backticks, quotes, and apostrophes freely —
# jq handles JSON-string-escaping AND this scripts own bash-quoting safely
# in one step, instead of the fragile `'\''`-per-apostrophe idiom the
# previous one-line version needed (every apostrophe in the reason text used
# to be a hand-matched escape triplet; this file already depends on jq for
# input parsing at the top, so it costs nothing new to depend on it here too).
REASON_BODY=$(cat <<REASONEOF
MULTI-AGENT SAFETY: ${PEER_COUNT} peer Claude session(s) share this repository checkout. Git target classification: shared/main checkout (not a linked worktree).

For git add: use specific files (not -A/-p/.).

For git commit: the canonical safe form is \`git commit --only -m "..." -- <paths>\` (bare \`git commit -m "..." -- <paths>\` is git-semantically identical — a pathspec given to git commit with no --only/-i already defaults to --only's behavior). This reads ONLY the current working-tree content of the named paths and disregards anything staged for other paths, so a peer's own pre-staged files can never sweep into this commit (2026-05-27 substrate-session sweep on 486973e; 2026-07-18 auto-checkpoint sweep on 754b702c).

If a peer has ALSO edited one of your target files (mixed authorship, same file): --only still reads that file's CURRENT working-tree content, which includes the peer's unstaged edits too — a pathspec does not protect against same-file hunks. Isolate your own hunks first with \`git add -p <file>\`, verify the index holds nothing else (\`git status\`), then a bare \`git commit\` (no pathspec) commits exactly what is staged.

For git checkout/restore (destructive): prefer Read + Edit to repair in place; if you must discard, run "git stash push -- <files>" first so it's reversible.

Completing a merge? bare commit is ALLOWED when MERGE_HEAD exists (git forbids --only there) — review git status first.
REASONEOF
)
jq -n --arg reason "$REASON_BODY" '{decision: "block", reason: $reason}'
exit 2
