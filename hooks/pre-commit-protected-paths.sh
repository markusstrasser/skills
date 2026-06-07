#!/usr/bin/env bash
# pre-commit-protected-paths.sh — tool-agnostic append-only + immutable-data
# enforcement on the staged diff. Standalone so any repo's existing pre-commit
# chain can call it as one step (genomics/phenome dispatchers do exactly that).
#
# WHY: Claude PreToolUse Write|Edit guards (append-only-guard, data-guard) do NOT
# reliably fire under Codex (decisions/2026-06-02-codex-cli-project-parity.md
# §FINAL). git pre-commit fires for ANY tool, so protection that must hold lives
# here too.
#
# Config: <repo-root>/.precommit-guards.env, parsed as INERT key=value (NEVER
# sourced — sourcing repo-controlled content is an RCE + lets an agent disable the
# guard; cross-model review 2026-06-07). Recognized keys (others ignored):
#   PRECOMMIT_APPENDONLY_PATHS  ERE regex; matching files may only GROW BY APPEND
#                               (block delete/rename, and any change to existing
#                                bytes — byte-prefix check, not line count)
#   PRECOMMIT_PROTECTED_PATHS   ERE regex; matching files immutable-once-written
#                               (block staged M/D/T/rename; new adds A allowed)
# The config file itself is ALWAYS protected (hardcoded) so it can't be neutered.
#
# Bypass: GIT_ALLOW_GUARD_BYPASS=1   Exit: 0 pass · 1 block.

set -uo pipefail

[ -n "${GIT_ALLOW_GUARD_BYPASS:-}" ] && { echo "[protected-paths] GIT_ALLOW_GUARD_BYPASS set — skipping" >&2; exit 0; }

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Read guard config from the COMMITTED (HEAD) version, NOT the mutable working tree:
# an agent that can write the repo must not be able to neuter enforcement by editing
# (even un-staging) .precommit-guards.env. Config changes take effect only after they
# are committed — and committing them requires GIT_ALLOW_GUARD_BYPASS (self-protected
# below). Bootstrap: fall back to the working-tree file when HEAD has none yet.
ENV_CONTENT="$(git show "HEAD:.precommit-guards.env" 2>/dev/null || true)"
if [ -z "$ENV_CONTENT" ] && [ -f "$REPO_ROOT/.precommit-guards.env" ]; then
    ENV_CONTENT="$(cat "$REPO_ROOT/.precommit-guards.env")"
fi

# Inert parser: extract a single recognized key's value WITHOUT shell evaluation.
# Accepts KEY='...' | KEY="..." | KEY=... on its own line; strips one layer of quotes.
# POSIX awk sub() has no backreferences — strip quotes with substr, not a capture group.
read_key() {
    printf '%s\n' "$ENV_CONTENT" | awk -v k="$1" -F= '
        /^[[:space:]]*#/ { next }
        $1==k {
            sub(/^[^=]*=/,""); val=$0
            if ((val ~ /^".*"$/) || (val ~ /^'\''.*'\''$/)) val=substr(val,2,length(val)-2)
            print val; exit }'
}

APPENDONLY="$(read_key PRECOMMIT_APPENDONLY_PATHS)"
PROTECTED="$(read_key PRECOMMIT_PROTECTED_PATHS)"

# Self-protection: the guard config is always immutable-once-written, regardless of
# (or even absent) its own PROTECTED pattern — an agent must not be able to edit it
# to disable enforcement. Prepend it to PROTECTED.
SELF='(^|/)\.precommit-guards\.env$'
PROTECTED="${PROTECTED:+$PROTECTED|}$SELF"

violations=()

# PROTECTED: immutable once written — block modify/delete/type-change/rename; allow new adds.
# --diff-filter=MDTR catches modify, delete, type-change (regular<->symlink), and rename.
while IFS= read -r path; do
    [ -z "$path" ] && continue
    echo "$path" | grep -qE "$PROTECTED" && violations+=("PROTECTED (immutable, no modify/delete/retype/rename): $path")
done < <(git diff --cached --name-only --diff-filter=MDTR -- 2>/dev/null)

if [ -n "$APPENDONLY" ]; then
    # Deletion / rename of an append-only file (--no-renames so a move shows as D).
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        echo "$path" | grep -qE "$APPENDONLY" && violations+=("APPEND-ONLY deleted: $path")
    done < <(git diff --cached --name-only --no-renames --diff-filter=DT -- 2>/dev/null)

    # Modification: the staged blob must START WITH the full HEAD blob (pure append).
    # Byte-prefix check — catches same-line-count rewrites that a line count misses.
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        echo "$path" | grep -qE "$APPENDONLY" || continue
        old_size=$(git cat-file -s "HEAD:$path" 2>/dev/null || echo 0)
        if ! cmp -s <(git cat-file blob "HEAD:$path" 2>/dev/null) \
                    <(git cat-file blob ":$path" 2>/dev/null | head -c "$old_size"); then
            violations+=("APPEND-ONLY existing content changed (not a pure append): $path")
        fi
    done < <(git diff --cached --name-only --no-renames --diff-filter=M -- 2>/dev/null)
fi

if [ "${#violations[@]}" -gt 0 ]; then
    echo "✗ pre-commit-protected-paths blocked the commit (tool-agnostic; protects Codex too):" >&2
    for v in "${violations[@]}"; do echo "  - $v" >&2; done
    echo "  override (deliberate, e.g. re-baselining a fixture / editing guard config): GIT_ALLOW_GUARD_BYPASS=1 git commit ..." >&2
    exit 1
fi
exit 0
