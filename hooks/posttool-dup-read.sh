#!/bin/bash
# PostToolUse:Read — detect repeated reads of the same file REGION, suggest Grep/offset.
# Warns at 4 identical reads and exits 2 at 6 (the read has already happened, so the exit
# only feeds the message back). Complements the PreToolUse tracker in
# pretool-universal-dispatch.py, which exempts offset reads.
# Tracks reads in /tmp per calling agent: in-process subagents share the CLI's PID, so a
# $PPID-only key counted seven siblings reading one shared brief as one caller (2026-09-21).
# Evidence: 8-10 occurrences across meta, genomics, selve (2026-03-20 → 2026-03-26)

INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)
KEY=$(printf '%s' "$INPUT" | jq -r '(.tool_input // {}) | "\(.file_path // ""):\(.offset // ""):\(.limit // "")"' 2>/dev/null || true)
[ -z "$FILE" ] && exit 0

. "$(dirname "$0")/lib_hook_identity.sh" 2>/dev/null || exit 0
hook_identity "$INPUT"
TRACKER="/tmp/claude-read-tracker-${HOOK_OWNER}"

# Track unique read signatures (file:offset:limit)
echo "$KEY" >> "$TRACKER"

# Count reads of same file with same offset+limit (true duplicates)
COUNT=$(grep -cF "$KEY" "$TRACKER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 6 ]; then
  "$(dirname "$0")/hook-trigger-log.sh" "dup-read-region" "block" "${COUNT}x ${FILE##*/}" 2>/dev/null || true
  echo "BLOCKED: Read ${FILE} (same region) ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit to target a different section." >&2
  exit 2
elif [ "$COUNT" -ge 4 ]; then
  "$(dirname "$0")/hook-trigger-log.sh" "dup-read-region" "warn" "${COUNT}x ${FILE##*/}" 2>/dev/null || true
  echo "{\"additionalContext\": \"Read ${FILE} (same region) ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit. Continued duplicate reads will be BLOCKED.\"}"
fi
exit 0
