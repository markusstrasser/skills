#!/bin/bash
# PostToolUse:Bash — detect repeated file-stat commands on the same path
# Catches: wc, ls, head, tail, stat, cat, du targeting the same file 3+ times
# Complements posttool-dup-read.sh which only catches Read tool calls.
# Evidence: 4 recurrences of poll-loop pattern (2026-03-06 → 2026-03-29)

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Extract file path from stat-like commands
# Matches: wc [-flags] /path, ls [-flags] /path, head/tail [-n N] /path, stat /path, cat /path, du /path
# Also: sleep N && wc /path (strip sleep prefix)
CMD_CLEAN=$(echo "$CMD" | sed 's/^sleep [0-9]*[smh]* *&&//' | sed 's/^ *//')
PATH_TARGET=$(echo "$CMD_CLEAN" | grep -oE '\b(wc|ls|head|tail|stat|cat|du)\b.*' | grep -oE '(/[^ |;>&]+)' | head -1)
[ -z "$PATH_TARGET" ] && exit 0

# Scope tracker per session + fork context to avoid cross-subagent false positives
# CLAUDE_AGENT_ID is set for subagents; fall back to PPID for main session
_SCOPE="${CLAUDE_AGENT_ID:-${CLAUDE_SESSION_ID:-$PPID}}"
TRACKER="/tmp/claude-bash-poll-tracker-${_SCOPE}"
echo "$PATH_TARGET" >> "$TRACKER"

COUNT=$(grep -cF "$PATH_TARGET" "$TRACKER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 5 ]; then
  echo "BLOCKED: Polled ${PATH_TARGET} ${COUNT}x via Bash this session. Use TaskOutput with block:true to wait for background tasks, or Read the file once when ready." >&2
  exit 2
elif [ "$COUNT" -ge 3 ]; then
  echo "{\"additionalContext\": \"Polled ${PATH_TARGET} ${COUNT}x via Bash. If waiting for a background task, use TaskOutput with block:true instead of polling. Next poll will be blocked.\"}"
fi
exit 0
