#!/usr/bin/env bash
# pretool-plan-protect.sh — Block rm/mv targeting plan & checkpoint markdown.
# Deploy as PreToolUse:Bash hook.
#
# Plans (.claude/plans/*.md, docs/ops/plans/*.md, .claude/checkpoint.md) are
# typically untracked and represent agent state that the user can't recover
# without manual paste-back. Block destructive Bash ops on these paths.
#
# Scope: blocks ONLY when a plan/checkpoint path is an ARGUMENT to an
# rm/mv/trash invocation — not when such a path merely appears elsewhere in the
# command line (e.g. `rm .scratch/x && wc -l .claude/plans/y.md` is allowed).
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

# Allow explicit override (user-acknowledged, e.g. cleanup of own plan)
echo "$CMD" | grep -q 'PLAN-PROTECT-OVERRIDE' && exit 0
[ "${PLAN_PROTECT_OVERRIDE:-}" = "ALLOW" ] && exit 0

# Block only if a protected path is an argument to a destructive command.
# Split the command on separators, then check each rm/mv/trash segment in
# isolation — so a plan path in a non-destructive segment (wc/grep/cat) passes.
HIT=$(CMD="$CMD" python3 <<'PY'
import os, re
cmd = os.environ.get("CMD", "")
segments = re.split(r'(?:&&|\|\||[;|\n])', cmd)
destructive = re.compile(r'^\s*(?:sudo\s+)?(?:rm|mv|trash)(?:\s|$)')
protected = re.compile(
    r'\.claude/plans/[^\s]*\.md|docs/ops/plans/[^\s]*\.md|\.claude/checkpoint\.md'
)
for seg in segments:
    if destructive.search(seg) and protected.search(seg):
        print("BLOCK")
        break
PY
)

if [ "$HIT" = "BLOCK" ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "plan-protect" "block" "$CMD" 2>/dev/null || true
    REASON='BLOCKED: rm/mv/trash targets a plan or checkpoint markdown (.claude/plans/, docs/ops/plans/, .claude/checkpoint.md). These are usually untracked agent state; recovery needs user paste-back. Use git mv for tracked files, or include PLAN-PROTECT-OVERRIDE to acknowledge the risk.'
    printf '{"decision":"block","reason":%s}\n' "$(printf '%s' "$REASON" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" >&2
    exit 2
fi

exit 0
