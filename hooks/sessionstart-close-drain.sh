#!/usr/bin/env bash
# SessionStart: drain RSI close-queue + nudge if prior session needs /rsi close.
# Async-friendly: runs digest drain in background, prints nudge to stdout for harness.
set +e
REPO="$HOME/Projects/agent-infra"
SCRIPT="$REPO/scripts/reflect_session_close.py"
[ -f "$SCRIPT" ] || exit 0

if [ "${CODEX_HOOK_COMPAT_SMOKE:-0}" = "1" ] || [ "${CLAUDE_HOOK_SMOKE:-0}" = "1" ]; then
  exit 0
fi

# Background drain — do not block session start
( python3 "$SCRIPT" --drain --limit 5 >/dev/null 2>&1 ) &

NUDGE=$(python3 "$SCRIPT" --nudge 2>/dev/null)
if [ -n "$NUDGE" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' \
    "$(printf '%s' "$NUDGE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
fi
exit 0
