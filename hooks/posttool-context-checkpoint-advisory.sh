#!/usr/bin/env bash
# posttool-context-checkpoint-advisory.sh — PostToolUse advisory.
# Gov-ID: hook:context-checkpoint-advisory
# goal: agent crosses a high-context threshold with no checkpoint, then auto-compacts mid-task and stalls
# verifier: null
# blast_radius: shared
#
# Hooks don't receive context% in their stdin payload — only the statusline does.
# statusline.sh tees the live value to /tmp/claude-ctxpct-<session_id>; this hook
# reads it and, ONCE per session per threshold, injects a one-line advisory to
# checkpoint now (the PreCompact hook auto-writes checkpoint.md, but a fresh
# checkpoint just before compaction loses less in-flight nuance). Advisory only —
# never blocks. Fires at 60% (prepare) and 80% (act).

trap 'exit 0' ERR

if [ "${CODEX_HOOK_COMPAT_SMOKE:-0}" = "1" ] || [ "${CLAUDE_HOOK_SMOKE:-0}" = "1" ]; then
  exit 0
fi

INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"
SID=$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print((json.load(sys.stdin) or {}).get("session_id",""))
except Exception: print("")' 2>/dev/null)
[ -z "$SID" ] && exit 0

PCT_FILE="/tmp/claude-ctxpct-${SID}"
[ -f "$PCT_FILE" ] || exit 0
PCT=$(cat "$PCT_FILE" 2>/dev/null || echo 0)
[[ "$PCT" =~ ^[0-9]+$ ]] || exit 0

STAMP="/tmp/claude-ctxadv-${SID}"
PREV=$(cat "$STAMP" 2>/dev/null || echo 0)
[[ "$PREV" =~ ^[0-9]+$ ]] || PREV=0

emit() {  # threshold message
  echo "$1" > "$STAMP"
  cat <<JSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"$2"}}
JSON
  exit 0
}

if (( PCT >= 80 && PREV < 80 )); then
  emit 80 "Context at ${PCT}%. Wrap up and commit in-flight work — if this is a long session approaching the window limit, an auto-compact will stop the turn. The PreCompact hook snapshots checkpoint.md, but a clean committed stopping point loses less."
elif (( PCT >= 40 && PREV < 40 )); then
  emit 40 "Context at ${PCT}% (~$(( PCT * 10 ))K on a 1M window). Good point to proactively /compact: auto-compact won't fire until near-full (~900K), and on the 1M tier input past 200K bills at 2×, so compacting now keeps context lean and cheap. Get to a committable point first — the PreCompact hook will snapshot checkpoint.md."
fi

exit 0
