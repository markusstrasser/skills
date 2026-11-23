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
# A script's `file(p).exists()` is a Read with offset 0 and limit 1 (probed 2026-11-23): an
# existence check, often polled in a wait loop, never content.
[ "$KEY" = "$FILE:0:1" ] && exit 0

. "$(dirname "$0")/lib_hook_identity.sh" 2>/dev/null || exit 0
hook_identity "$INPUT"
TRACKER="/tmp/claude-read-tracker-${HOOK_OWNER}"

# Track read signatures (file:offset:limit) with the time of the read.
printf '%s\t%s\n' "$KEY" "$(date +%s)" >> "$TRACKER"

# Count reads of the same region since the file last changed. A read after an edit is not a
# duplicate: a session that edits a file and re-reads it to check drew the warning, and
# then the block, on correct work (2026-11-23, a script re-reading the hook it was editing).
# A missing file has mtime 0, so every read of it counts.
MTIME=$(stat -f %m "$FILE" 2>/dev/null || stat -c %Y "$FILE" 2>/dev/null || echo 0)
COUNT=$(awk -F'\t' -v k="$KEY" -v m="$MTIME" '$1 == k && ($2 == "" || $2 + 0 >= m + 0) { c++ } END { print c + 0 }' "$TRACKER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 6 ]; then
  "$(dirname "$0")/hook-trigger-log.sh" "dup-read-region" "block" "${COUNT}x ${FILE##*/}" 2>/dev/null || true
  echo "BLOCKED: Read ${FILE} (same region) ${COUNT}x this session. Use Grep to find specific content, or Read with offset/limit to target a different section." >&2
  exit 2
elif [ "$COUNT" -ge 4 ]; then
  "$(dirname "$0")/hook-trigger-log.sh" "dup-read-region" "warn" "${COUNT}x ${FILE##*/}" 2>/dev/null || true
  jq -n --arg f "$FILE" --arg c "$COUNT" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: ("Read " + $f + " (same region) " + $c + "x this session. Use Grep to find specific content, or Read with offset/limit. Continued duplicate reads will be BLOCKED.")}}'
fi
exit 0
