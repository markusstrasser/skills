#!/usr/bin/env bash
# posttool-context-checkpoint-advisory.sh — PostToolUse advisory.
# Gov-ID: hook:context-checkpoint-advisory
# goal: agent crosses a high-context threshold with no checkpoint, then auto-compacts mid-task and stalls
# verifier: null
# blast_radius: shared
#
# Hooks don't receive context% in their stdin payload — only the statusline does.
# statusline.sh tees "pct|tokens|window" to /tmp/claude-ctxpct-<session_id>; this
# hook reads it and nudges to checkpoint / proactively /compact. Window-relative
# thresholds (40% prepare, 80% backstop) so it's correct in any window (200K or 1M).
# Re-arms after a /compact drops context (the whole point is the compact-refill
# cycle, so it must fire again each cycle). Advisory only — never blocks.

trap 'exit 0' ERR

if [ "${CODEX_HOOK_COMPAT_SMOKE:-0}" = "1" ] || [ "${CLAUDE_HOOK_SMOKE:-0}" = "1" ]; then
  exit 0
fi

INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"
SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null || echo "")
[ -z "$SID" ] && exit 0

PCT_FILE="/tmp/claude-ctxpct-${SID}"
[ -f "$PCT_FILE" ] || exit 0
# `|| true`: the statusline tees without a trailing newline, so read returns
# non-zero at EOF (vars are still populated) — without this the ERR trap fires.
IFS='|' read -r PCT TOKENS WINDOW < "$PCT_FILE" || true
[[ "$PCT" =~ ^[0-9]+$ ]] || exit 0
[[ "$TOKENS" =~ ^[0-9]+$ ]] || TOKENS=0
[[ "$WINDOW" =~ ^[0-9]+$ ]] || WINDOW=0

STAMP="/tmp/claude-ctxadv-${SID}"
PREV=$(cat "$STAMP" 2>/dev/null || echo 0)
[[ "$PREV" =~ ^[0-9]+$ ]] || PREV=0

# Re-arm: if context dropped well below the last-fired threshold (a /compact
# happened), reset the stamp so the next climb re-fires. Without this the hook
# fires once per session and is silent for every subsequent compact-refill cycle.
if (( PCT < PREV - 10 )); then
  PREV=0
  echo 0 > "$STAMP"
fi

# Human-readable absolute size, e.g. "412K"
human() { if (( $1 >= 1000 )); then echo "$(( $1 / 1000 ))K"; else echo "$1"; fi; }
ABS=""
(( TOKENS > 0 && WINDOW > 0 )) && ABS=" (~$(human "$TOKENS") of a $(human "$WINDOW") window)"

emit() {  # threshold message — json.dumps the body so a future quote can't break the JSON
  echo "$1" > "$STAMP"
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":%s}}\n' \
    "$(printf '%s' "$2" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
  exit 0
}

if (( PCT >= 80 && PREV < 80 )); then
  emit 80 "Context at ${PCT}%${ABS}. Wrap up and commit in-flight work — if you're near the window limit an auto-compact will stop the turn. The PreCompact hook snapshots checkpoint.md, but a clean committed stopping point loses less."
elif (( PCT >= 40 && PREV < 40 )); then
  emit 40 "Context at ${PCT}%${ABS}. Good point to reach a committable stopping point and consider /compact — keeping context lean now beats a mid-task compaction later. The PreCompact hook will snapshot checkpoint.md regardless."
fi

exit 0
