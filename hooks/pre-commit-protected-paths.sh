#!/usr/bin/env bash
# pre-commit-protected-paths.sh — tool-agnostic append-only + immutable-data
# enforcement on the staged diff. Standalone so any repo's existing pre-commit
# chain can call it as one step (genomics/phenome dispatchers do exactly that).
#
# WHY: Claude PreToolUse Write|Edit guards (append-only-guard, data-guard) do NOT
# reliably fire under Codex (decisions/2026-06-02-codex-cli-project-parity.md
# §FINAL: file-edit PreToolUse hooks did not fire; --dangerously-bypass-approvals-
# and-sandbox disables hooks). git pre-commit fires for ANY tool, so protection
# that must hold lives here too.
#
# Config (env, or sourced from <repo-root>/.precommit-guards.env):
#   PRECOMMIT_APPENDONLY_PATHS  ERE regex; matching files may only grow
#                               (block deletion / line-count shrink vs HEAD)
#   PRECOMMIT_PROTECTED_PATHS   ERE regex; matching files immutable-once-written
#                               (block staged M/R/D; new adds A are allowed)
#
# Bypass: GIT_ALLOW_GUARD_BYPASS=1   Exit: 0 pass · 1 block.

set -uo pipefail

[ -n "${GIT_ALLOW_GUARD_BYPASS:-}" ] && { echo "[protected-paths] GIT_ALLOW_GUARD_BYPASS set — skipping" >&2; exit 0; }

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ -f "$REPO_ROOT/.precommit-guards.env" ]; then
    # shellcheck disable=SC1090,SC1091
    . "$REPO_ROOT/.precommit-guards.env"
fi

APPENDONLY="${PRECOMMIT_APPENDONLY_PATHS:-}"
PROTECTED="${PRECOMMIT_PROTECTED_PATHS:-}"
[ -z "$APPENDONLY" ] && [ -z "$PROTECTED" ] && exit 0

violations=()

if [ -n "$PROTECTED" ]; then
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        echo "$path" | grep -qE "$PROTECTED" && violations+=("PROTECTED (immutable, no modify/delete): $path")
    done < <(git diff --cached --name-only --no-renames --diff-filter=MD)
fi

if [ -n "$APPENDONLY" ]; then
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        echo "$path" | grep -qE "$APPENDONLY" && violations+=("APPEND-ONLY deleted: $path")
    done < <(git diff --cached --name-only --diff-filter=D)

    while IFS= read -r path; do
        [ -z "$path" ] && continue
        echo "$path" | grep -qE "$APPENDONLY" || continue
        old=$(git show "HEAD:$path" 2>/dev/null | wc -l | tr -d ' ')
        new=$(git cat-file blob ":$path" 2>/dev/null | wc -l | tr -d ' ')
        [ "${new:-0}" -lt "${old:-0}" ] && violations+=("APPEND-ONLY shrank (${old}→${new} lines): $path")
    done < <(git diff --cached --name-only --diff-filter=M)
fi

if [ "${#violations[@]}" -gt 0 ]; then
    echo "✗ pre-commit-protected-paths blocked the commit (tool-agnostic; protects Codex too):" >&2
    for v in "${violations[@]}"; do echo "  - $v" >&2; done
    echo "  override (deliberate, e.g. re-baselining a fixture): GIT_ALLOW_GUARD_BYPASS=1 git commit ..." >&2
    exit 1
fi
exit 0
