#!/usr/bin/env bash
# precommit-plan-completion-guard.sh — Detect "Status: completed" on plans with
# unchecked items. ADVISORY-FIRST per Constitution §10. Triggered as
# PreToolUse:Bash hook on `git commit*` invocations.
#
# Detects: any staged file matching docs/ops/plans/**/*.md or .claude/plans/**/*.md
#   that contains "Status: (done|completed)" AND has unchecked "- [ ]" items.
# Rationale: 3rd recurrence of premature plan-closure across Codex + Claude.
# Bypass (when later promoted to blocking): FORCE_PLAN_COMPLETE=1 env var.

set -uo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command","")[:500])' 2>/dev/null || echo "")
[ -z "$COMMAND" ] && exit 0
echo "$COMMAND" | grep -qE '(^|[[:space:]&;|])git[[:space:]]+commit' || exit 0

# Find staged plan files
STAGED_PLANS=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null \
    | grep -E '(^|/)docs/ops/plans/.*\.md$|(^|/)\.claude/plans/.*\.md$' || true)
[ -z "$STAGED_PLANS" ] && exit 0

VIOLATIONS=""
while IFS= read -r f; do
    [ -z "$f" ] || [ ! -f "$f" ] && continue
    if grep -qiE '^[[:space:]]*\*\*?Status:?\*\*?[[:space:]]*[`\(]?[[:space:]]*(done|completed)' "$f" 2>/dev/null; then
        UNCHECKED=$(grep -cE '^[[:space:]]*-[[:space:]]+\[[[:space:]]\]' "$f" 2>/dev/null || echo 0)
        if [ "$UNCHECKED" -gt 0 ]; then
            VIOLATIONS="${VIOLATIONS}${f}: $UNCHECKED unchecked items\n"
        fi
    fi
done <<< "$STAGED_PLANS"

if [ -n "$VIOLATIONS" ]; then
    echo "ADVISORY: plan(s) marked Status: completed but contain unchecked items:" >&2
    printf "$VIOLATIONS" >&2
    echo "Run /critique close or finish the unchecked items before marking complete." >&2
    echo "Bypass (when promoted to blocking): FORCE_PLAN_COMPLETE=1 git commit ..." >&2
    ~/Projects/skills/hooks/hook-trigger-log.sh "plan-completion-guard" "warn" "$(echo "$VIOLATIONS" | head -c 120 | tr '\n' '|')" 2>/dev/null || true
fi
exit 0
