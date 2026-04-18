#!/usr/bin/env bash
# pretool-destructive-git-ref.sh — Warn on destructive git ops with unstable refs
# in multi-agent sessions. ADVISORY-FIRST per Constitution §10 (fail open).
# Promotion to blocking (exit 2) requires baseline FP measurement.
#
# Triggered: PreToolUse:Bash globally (~/.claude/settings.json)
# Detects: git revert/reset --hard/checkout -- with HEAD or branch-tip arg,
#   when 2+ claude processes are running.
# Rationale: HEAD is not stable under concurrency. See improvement-log
#   2026-04-11 entry "BLIND DESTRUCTIVE GIT REF IN MULTI-AGENT SESSION".
# Limits: regex bypassable via aliases/eval; agents do not use these.

set -uo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command","")[:500])' 2>/dev/null || echo "")
[ -z "$COMMAND" ] && exit 0

# Match: git (revert|reset --hard|checkout --) ... with HEAD/HEAD~N/branch-tip arg
if echo "$COMMAND" | grep -qE '(^|[[:space:]&;|])git[[:space:]]+(revert|reset[[:space:]]+--(hard|mixed)|checkout[[:space:]]+--)[[:space:]]+(HEAD([~^][0-9]*)?|[a-z][a-z0-9_/-]*)([[:space:]]|$)'; then
    AGENT_COUNT=$(pgrep -f 'claude ' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$AGENT_COUNT" -ge 2 ]; then
        echo "ADVISORY: destructive git op with unstable ref in multi-agent session ($AGENT_COUNT agents)." >&2
        echo "HEAD is not stable under concurrency — another agent may have advanced it." >&2
        echo "Recommended: git log --oneline -5  →  pass explicit commit hash." >&2
        echo "Example: git revert 82777db1  (not: git revert HEAD)" >&2
        ~/Projects/skills/hooks/hook-trigger-log.sh "destructive-git-ref" "warn" "agents=$AGENT_COUNT cmd=$(echo "$COMMAND" | head -c 80)" 2>/dev/null || true
    fi
fi
exit 0
