#!/bin/bash
# PostToolUse:Read — detect 3+ reads of same file, suggest Grep/offset
# Advisory only. Tracks reads in /tmp keyed by parent PID (stable per session).
# Evidence: 8-10 occurrences across meta, genomics, selve (2026-03-20 → 2026-03-26)

INPUT=$(cat)
eval "$(echo "$INPUT" | python3 -c "
import sys,json
ti = json.load(sys.stdin).get('tool_input',{})
fp = ti.get('file_path','')
off = ti.get('offset','')
lim = ti.get('limit','')
print(f\"FILE='{fp}'\")
print(f\"KEY='{fp}:{off}:{lim}'\")
" 2>/dev/null)"
[ -z "$FILE" ] && exit 0

TRACKER="/tmp/claude-read-tracker-${PPID}"

# Track unique read signatures (file:offset:limit)
echo "$KEY" >> "$TRACKER"

# Count reads of same file with same offset+limit (true duplicates)
COUNT=$(grep -cF "$KEY" "$TRACKER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 6 ]; then
  echo "BLOCKED: Read ${FILE} (same region) ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit to target a different section." >&2
  exit 2
elif [ "$COUNT" -ge 4 ]; then
  echo "{\"additionalContext\": \"Read ${FILE} (same region) ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit. Continued duplicate reads will be BLOCKED.\"}"
fi
exit 0
