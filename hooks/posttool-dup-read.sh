#!/bin/bash
# PostToolUse:Read — detect 3+ reads of same file, suggest Grep/offset
# Advisory only. Tracks reads in /tmp keyed by parent PID (stable per session).
# Evidence: 8-10 occurrences across meta, genomics, selve (2026-03-20 → 2026-03-26)

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$FILE" ] && exit 0

TRACKER="/tmp/claude-read-tracker-${PPID}"
echo "$FILE" >> "$TRACKER"

COUNT=$(grep -cF "$FILE" "$TRACKER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 4 ]; then
  echo "BLOCKED: Read ${FILE} ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit to target the section you need." >&2
  exit 2
elif [ "$COUNT" -ge 3 ]; then
  echo "{\"additionalContext\": \"Read ${FILE} ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit. Next read of this file will be BLOCKED.\"}"
fi
exit 0
