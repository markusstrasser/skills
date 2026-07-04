#!/bin/bash
# PostToolUse:Bash — portfolio nudge at the background-dispatch decision point.
# When the MAIN session dispatches run_in_background work, the recurring failure is
# ending the turn "waiting for notification" with zero parallel fronts (operator-flagged
# 4x: 2026-06-17, 2026-06-19 x2, 2026-07-04 "I don't get this waiting... #g #f").
# Instruction-level fixes failed per their own pre-registered kill rule
# (~/.claude/rules/wakeup-cadence.md tick-open self-check, retired 2026-07-04) — this
# hook is the structural replacement: one advisory line AT the dispatch, in-turn,
# so the model can still act on it before yielding.
#
# Iatrogenic guards: advisory only (never blocks); suppressed for subagents (the
# portfolio rule binds the PARENT); deduped to one nudge per 15 min per session.

INPUT=$(cat)

# Subagents dispatch background work as part of THEIR task — never nag them.
[ -n "$CLAUDE_AGENT_ID" ] && exit 0

BG=$(printf '%s' "$INPUT" | jq -r '.tool_input.run_in_background // false' 2>/dev/null)
[ "$BG" != "true" ] && exit 0

_SCOPE="${CLAUDE_SESSION_ID:-$PPID}"
MARKER="/tmp/claude-bg-portfolio-nudge-${_SCOPE}"
NOW=$(date +%s)
if [ -f "$MARKER" ]; then
  LAST=$(cat "$MARKER" 2>/dev/null || echo 0)
  [ $((NOW - LAST)) -lt 900 ] && exit 0
fi
echo "$NOW" > "$MARKER"

printf '{"additionalContext": "PORTFOLIO (background dispatch detected): before ending this turn waiting on it, advance another front in parallel — grind/heretic/dreamer/meta via subagents or llmx (open rows: `just backlog list --open`). Ending the turn with this dispatch as the only live front requires high-conviction \\"nothing to parallelize\\", stated explicitly."}'
exit 0
