#!/usr/bin/env bash
# pre-commit-guards.sh — tool-agnostic git pre-commit enforcement of critical guards.
#
# WHY: Claude PreToolUse Write|Edit guards (data-guard, append-only-guard) do NOT
# reliably fire under Codex — empirically, file-edit (apply_patch) PreToolUse hooks
# did not fire, and --dangerously-bypass-approvals-and-sandbox disables hooks
# entirely (decisions/2026-06-02-codex-cli-project-parity.md §FINAL). A git
# pre-commit hook fires on `git commit` regardless of which agent/tool made the
# edit (Claude, Codex, manual) — so protection that MUST hold lives HERE, not only
# in PreToolUse hooks.
#
# Chains pre-commit-no-large-binaries.sh, then enforces, on the STAGED diff:
#   - PRECOMMIT_APPENDONLY_PATHS  ERE regex; matching files may only grow
#                                 (block deletion or line-count shrink vs HEAD)
#   - PRECOMMIT_PROTECTED_PATHS   ERE regex; matching files are immutable-once-written
#                                 (block staged M/R/D; new files A are allowed — ingestion)
# Config is read from env, or sourced from <repo-root>/.precommit-guards.env.
#
# Install:  ln -sf ~/Projects/skills/hooks/pre-commit-guards.sh .git/hooks/pre-commit
#           (agent-infra: `just install-hooks`)
# Bypass:   GIT_ALLOW_GUARD_BYPASS=1 git commit ...
# Exit:     0 pass · 1 block

set -uo pipefail
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1) Chain the binary guard (preserve existing behavior). Its own bypass var still works.
if [ -x "$HOOKS_DIR/pre-commit-no-large-binaries.sh" ]; then
    "$HOOKS_DIR/pre-commit-no-large-binaries.sh" || exit 1
fi

if [ -n "${GIT_ALLOW_GUARD_BYPASS:-}" ]; then
    echo "[pre-commit-guards] GIT_ALLOW_GUARD_BYPASS set — skipping append-only/protected checks" >&2
    exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ -f "$REPO_ROOT/.precommit-guards.env" ]; then
    # shellcheck disable=SC1090,SC1091
    . "$REPO_ROOT/.precommit-guards.env"
fi

APPENDONLY="${PRECOMMIT_APPENDONLY_PATHS:-}"
PROTECTED="${PRECOMMIT_PROTECTED_PATHS:-}"
[ -z "$APPENDONLY" ] && [ -z "$PROTECTED" ] && exit 0

violations=()

# Protected paths: immutable once written — block modify/rename/delete, allow new adds.
if [ -n "$PROTECTED" ]; then
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        if echo "$path" | grep -qE "$PROTECTED"; then
            violations+=("PROTECTED (immutable, no modify/delete): $path")
        fi
    done < <(git diff --cached --name-only --no-renames --diff-filter=MD)
fi

# Append-only paths: block deletion or line-count shrink vs HEAD.
if [ -n "$APPENDONLY" ]; then
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        if echo "$path" | grep -qE "$APPENDONLY"; then
            violations+=("APPEND-ONLY deleted: $path")
        fi
    done < <(git diff --cached --name-only --diff-filter=D)

    while IFS= read -r path; do
        [ -z "$path" ] && continue
        echo "$path" | grep -qE "$APPENDONLY" || continue
        old=$(git show "HEAD:$path" 2>/dev/null | wc -l | tr -d ' ')
        new=$(git cat-file blob ":$path" 2>/dev/null | wc -l | tr -d ' ')
        if [ "${new:-0}" -lt "${old:-0}" ]; then
            violations+=("APPEND-ONLY shrank (${old}→${new} lines): $path")
        fi
    done < <(git diff --cached --name-only --diff-filter=M)
fi

if [ "${#violations[@]}" -gt 0 ]; then
    echo "✗ pre-commit-guards blocked the commit (tool-agnostic; protects Codex too):" >&2
    for v in "${violations[@]}"; do echo "  - $v" >&2; done
    echo "  override (deliberate): GIT_ALLOW_GUARD_BYPASS=1 git commit ..." >&2
    exit 1
fi
exit 0
