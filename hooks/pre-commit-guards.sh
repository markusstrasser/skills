#!/usr/bin/env bash
# pre-commit-guards.sh — universal git pre-commit dispatcher for repos WITHOUT a
# richer repo-specific chain (agent-infra, intel). Repos that already have a chain
# (genomics .claude/hooks/run-git-pre-commit.sh, phenome scripts/hooks/
# pre-commit-chain.sh) instead call pre-commit-protected-paths.sh directly as one
# of their steps — don't point those at this dispatcher (it lacks their checks).
#
# Chains (abort on first failure unless noted):
#   1. pre-commit-no-large-binaries.sh   — reject PDFs / large binaries
#   2. validate-changed-hooks.sh         — staged hook scripts must parse
#   3. pre-commit-protected-paths.sh     — append-only + immutable-data enforcement
#   4. pre-commit-deid-guard.sh          — block subject name/sample-ID in research memos (opt-in)
#   5. pre-commit-codebase-map.sh        — refresh agent codebase maps (fail-open)
#
# All are repo-agnostic. Steps 1/2 self-skip when nothing applies; step 3 reads
# <repo-root>/.precommit-guards.env; step 4 self-skips unless <repo-root>/.deid-guard.env
# exists (so only opt-in repos like substrate enforce it). See pre-commit-protected-paths.sh
# for why commit-time enforcement matters (Codex hook firing is unreliable). The de-id step
# specifically covers the auto-`[wip]` checkpoint, which commits via a bare `git commit`
# (no --no-verify) and so cannot be guarded by a PreToolUse-on-commit hook alone.
#
# Install (agent-infra): `just install-hooks`. Bypass: GIT_ALLOW_GUARD_BYPASS=1.
# Exit: 0 pass · 1 block.

set -uo pipefail
# Resolve through symlinks: when installed as a `.git/hooks/pre-commit` SYMLINK,
# BASH_SOURCE[0] is the symlink path whose dirname is .git/hooks/ — NOT where the
# sibling step scripts live. Canonicalizing makes HOOKS_DIR point at the real
# skills/hooks dir, so the step loop actually finds and runs them. (Without this,
# the whole chain silently no-ops under symlink install — substrate did, 2026-06-10
# → 2026-06-29.) Non-symlink (copied) installs are unaffected: the loop is skipped.
_src="${BASH_SOURCE[0]}"
while [ -L "$_src" ]; do
    _ld="$(cd -P "$(dirname "$_src")" && pwd)"
    _src="$(readlink "$_src")"
    case "$_src" in /*) ;; *) _src="$_ld/$_src" ;; esac
done
HOOKS_DIR="$(cd -P "$(dirname "$_src")" && pwd)"

for step in pre-commit-no-large-binaries.sh validate-changed-hooks.sh pre-commit-protected-paths.sh pre-commit-deid-guard.sh pre-commit-codebase-map.sh; do
    if [ -x "$HOOKS_DIR/$step" ]; then
        if [ "$step" = "pre-commit-codebase-map.sh" ]; then
            "$HOOKS_DIR/$step" || true
        else
            "$HOOKS_DIR/$step" || exit 1
        fi
    fi
done
exit 0
