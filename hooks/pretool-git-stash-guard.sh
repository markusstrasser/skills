#!/usr/bin/env bash
# pretool-git-stash-guard.sh — PreToolUse(Bash) hook.
# Gov-ID: hook:git-stash-guard
# goal: a bare `git stash` (or stash pop/apply/drop/clear) in a checkout shared
#       with a live peer sweeps the PEER's uncommitted work, not just the
#       caller's — same class as `git add -A`, but worse: stash is tree-wide
#       and cannot be path-limited by default, and `stash pop` against a peer's
#       meanwhile-committed changes FAILS (leaves UU markers) rather than
#       restoring anything. ~/.claude/CLAUDE.md <git_rules> (2026-07-16 entry)
#       bans bare `git stash` in a shared checkout for exactly this reason.
# verifier: skills/hooks/test_pretool_git_stash_guard.py + test_bash_dispatch.py
# blast_radius: shared
#
# Blocking contract: exit 2 with a message on stderr re-prompts the model.
# Exit 0 (silent) = allow (no peer, or a path-limited `stash push -- <paths>`).
# Fails open on parse errors / peer-detector errors (advisory-only degrade).
#
# Shape cloned deliberately from pretool-git-add-all-guard.sh (same
# shlex-segment-scan pattern, same jq-free python3 stdin block) — see that
# file's own header for the pattern this one repeats. The one structural
# difference: this guard is PEER-CONDITIONAL (git add -A is banned always;
# git stash is banned only when a peer shares the checkout — a solo session's
# own stash is reversible by the same session), so it shells out to
# peer-session-count.sh (the SSOT peer detector, already wired into
# pretool-multiagent-commit-guard.sh) exactly on the rare path where a
# stash-shaped command is seen — zero added subprocess cost on the non-stash
# majority of Bash calls.
#
# NOTE: no `trap 'exit 0' ERR` here — it would swallow Python's exit 2
# (documented gotcha in ~/.claude/CLAUDE.md, same note as git-add-all-guard.sh).

INPUT=$(cat)

VERDICT=$(python3 - "$INPUT" <<'PY'
import sys, json, re, shlex

try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input", {}) or {}).get("command", "")
if not cmd or "stash" not in cmd:
    sys.exit(0)

# Split into segments on shell separators so `git stash && ...` is caught.
segments = re.split(r"&&|\|\||;|\||\n", cmd)


def stash_call(seg: str):
    """Return (is_git_stash, subcommand_args) for a segment, or (False, None)."""
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        # Unparseable segment — cheap regex fallback, anchored to segment start.
        if re.match(r"(?:[A-Za-z_]\w*=\S+\s+)*git\s+(-\S+\s+)*stash\b", seg):
            return True, None
        return False, None
    i = 0
    while i < len(parts) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", parts[i]):
        i += 1
    if i >= len(parts) or parts[i] != "git":
        return False, None
    j = i + 1
    while j < len(parts) and parts[j].startswith("-"):
        j += 2 if parts[j] in ("-C", "-c") else 1
    if j >= len(parts) or parts[j] != "stash":
        return False, None
    return True, parts[j + 1:]


_READONLY_STASH_SUBCMDS = {"list", "show"}


def is_safe_pathlimited_push(args) -> bool:
    """Two allowed shapes, everything else is peer-gated:
      1. `git stash list` / `git stash show [ref]` — read-only, touches
         neither the working tree nor another stash entry.
      2. `git stash push -- <paths>` (or `save -- <paths>`, git's legacy
         alias) — path-limited, so it cannot sweep a peer's OTHER files.
    Bare `push`/`save` without `--` still globs the whole index (git's own
    default), and pop/apply/drop/clear/branch/create/store all touch
    state that isn't necessarily the caller's — none of those are safe."""
    if args is None:
        return False
    if not args:
        return False  # bare `git stash` == `git stash push` on the WHOLE tree
    sub = args[0]
    if sub in _READONLY_STASH_SUBCMDS:
        return True
    if sub not in ("push", "save"):
        return False  # pop/apply/drop/branch/clear/create/store — never path-limited
    return "--" in args[1:]


offending_stash = False
for seg in segments:
    hit, args = stash_call(seg)
    if not hit:
        continue
    if not is_safe_pathlimited_push(args):
        offending_stash = True
        break

if offending_stash:
    print("STASH_SEEN")
sys.exit(0)
PY
)
rc=$?

if [ "$rc" -ne 0 ] || [ "$VERDICT" != "STASH_SEEN" ]; then
    exit 0
fi

# Rare path only: an offending (non-path-limited) `git stash` subcommand was seen.
# Resolve peer count via the single-sourced detector (same contract used by
# pretool-multiagent-commit-guard.sh: PEER_SESSION_COUNT_BIN override for tests).
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PEER_SESSION_COUNT_BIN="${PEER_SESSION_COUNT_BIN:-$HOOK_DIR/peer-session-count.sh}"
CWD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print((d.get("tool_input",{}) or {}).get("workdir") or d.get("cwd") or "")
except Exception:
    print("")' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"
PEER_COUNT=$("$PEER_SESSION_COUNT_BIN" "$CWD" 2>/dev/null || echo 0)
[[ "$PEER_COUNT" =~ ^[0-9]+$ ]] || PEER_COUNT=0

if [ "$PEER_COUNT" -lt 1 ]; then
    # Solo session: never block your own stash — advisory note only (spec:
    # "when no peers, advisory note only"), so the habit is nudged before a
    # peer ever joins this checkout, not just punished after the fact.
    python3 -c 'import json; print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "git-stash-guard: bare `git stash` is tree-wide and cannot be path-limited by default (no peer detected right now, so this is allowed) — prefer `git stash push -- <paths>` so it stays safe if a peer joins this checkout later (global <git_rules>, CLAUDE.md 2026-07-16 entry)."}}))'
    exit 0
fi

~/Projects/skills/hooks/hook-trigger-log.sh "git-stash-guard" "block" \
    "peers=$PEER_COUNT cmd=$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    print(((json.load(sys.stdin).get("tool_input",{}) or {}).get("command") or "")[:80])
except Exception:
    print("")' 2>/dev/null)" 2>/dev/null || true

cat >&2 <<MSG
BLOCK: bare \`git stash\` (or stash pop/apply/drop/clear) is banned in a
checkout with $PEER_COUNT live peer Claude session(s) sharing it (global
<git_rules> — CLAUDE.md, 2026-07-16 entry). \`git stash\` is tree-wide and
cannot be path-limited by default; it silently rips a peer's in-flight edits
out from under a live session, and \`stash pop\` against whatever the peer
commits meanwhile FAILS (leaves UU conflict markers) rather than restoring
anything.

Safe alternatives:
  - \`git stash push -- <your-paths>\`   (path-limited to files you own — ALWAYS allowed)
  - a git worktree for the A/B you're trying to do
  - \`git show HEAD:<file>\`             (read the committed version without touching the tree)

If you already ran a bare stash: do NOT resolve a peer's conflict yourself —
\`git checkout HEAD -- <file>\` to clear it, leave their stash entry intact,
save \`git stash show -p\` to a patch outside git, and tell the operator.
MSG
exit 2
