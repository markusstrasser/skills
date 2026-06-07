#!/usr/bin/env bash
# pre-commit-guards.sh — universal git pre-commit dispatcher for repos WITHOUT a
# richer repo-specific chain (agent-infra, intel). Repos that already have a chain
# (genomics .claude/hooks/run-git-pre-commit.sh, phenome scripts/hooks/
# pre-commit-chain.sh) instead call pre-commit-protected-paths.sh directly as one
# of their steps — don't point those at this dispatcher (it lacks their checks).
#
# Chains (abort on first failure):
#   1. pre-commit-no-large-binaries.sh   — reject PDFs / large binaries
#   2. validate-changed-hooks.sh         — staged hook scripts must parse
#   3. pre-commit-protected-paths.sh     — append-only + immutable-data enforcement
#
# All three are repo-agnostic. Steps 1/2 self-skip when nothing applies; step 3
# reads <repo-root>/.precommit-guards.env. See pre-commit-protected-paths.sh for
# why commit-time enforcement matters (Codex hook firing is unreliable).
#
# Install (agent-infra): `just install-hooks`. Bypass: GIT_ALLOW_GUARD_BYPASS=1.
# Exit: 0 pass · 1 block.

set -uo pipefail
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for step in pre-commit-no-large-binaries.sh validate-changed-hooks.sh pre-commit-protected-paths.sh; do
    [ -x "$HOOKS_DIR/$step" ] && { "$HOOKS_DIR/$step" || exit 1; }
done
exit 0
