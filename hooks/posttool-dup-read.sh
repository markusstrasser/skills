#!/bin/bash
# PostToolUse:Read — detect 3+ reads of same file, suggest Grep/offset
# Advisory only. Tracks reads in /tmp keyed by parent PID (stable per session).
# Evidence: 8-10 occurrences across meta, genomics, selve (2026-03-20 → 2026-03-26)

INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)
KEY=$(printf '%s' "$INPUT" | jq -r '(.tool_input // {}) | "\(.file_path // ""):\(.offset // ""):\(.limit // "")"' 2>/dev/null || true)
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
