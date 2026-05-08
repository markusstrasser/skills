#!/usr/bin/env bash
# pretool-plan-protect.sh — Block rm/mv targeting plan & checkpoint markdown.
# Deploy as PreToolUse:Bash hook.
#
# Plans (.claude/plans/*.md, docs/ops/plans/*.md, .claude/checkpoint.md) are
# typically untracked and represent agent state that the user can't recover
# without manual paste-back. Block destructive Bash ops on these paths.
#
# Override: set PLAN_PROTECT_OVERRIDE=ALLOW in command env, or include the
# literal token "PLAN-PROTECT-OVERRIDE" in the command string.
#
# Exit 2 = block. Exit 0 = pass. Fails open on error.

trap 'exit 0' ERR

INPUT=$(cat)

CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

[ -z "$CMD" ] && exit 0

# Only inspect destructive ops as the operative command (not buried in args).
# Match: leading rm/mv, or rm/mv after a command separator (;, &&, ||, |).
echo "$CMD" | grep -qE '(^|;|&&|\|\|)[[:space:]]*(rm|mv|trash)[[:space:]]' || exit 0

# Allow explicit override (user-acknowledged, e.g. cleanup of own plan)
echo "$CMD" | grep -q 'PLAN-PROTECT-OVERRIDE' && exit 0
[ "${PLAN_PROTECT_OVERRIDE:-}" = "ALLOW" ] && exit 0

# Match plan/checkpoint paths in any quoting style
PROTECTED_RE='\.claude/plans/[^[:space:]]*\.md|docs/ops/plans/[^[:space:]]*\.md|\.claude/checkpoint\.md'
if echo "$CMD" | grep -qE "$PROTECTED_RE"; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "plan-protect" "block" "$CMD" 2>/dev/null || true
    REASON='BLOCKED: rm/mv on plan or checkpoint markdown. These files are usually untracked agent state and recovery requires user paste-back. Use git mv if renaming a tracked file, or include PLAN-PROTECT-OVERRIDE in the command to acknowledge the risk.'
    printf '{"decision":"block","reason":%s}\n' "$(printf '%s' "$REASON" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" >&2
    exit 2
fi

exit 0
