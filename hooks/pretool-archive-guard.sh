#!/usr/bin/env bash
# pretool-archive-guard.sh — Block git mv of analysis docs to archive dirs.
# Deploy as PreToolUse hook on Bash.
#
# Env: ARCHIVE_PROTECTED (pipe-separated regex for protected source dirs, required)
#      ARCHIVE_TARGET    (regex for target dir, default: "archive")
#      ARCHIVE_OVERRIDE  (override keyword, default: "ARCHIVAL-REVIEWED")
#      ARCHIVE_MSG       (custom block reason, optional)
#
# Exit 2 = block. Exit 0 = pass. Fails open on error.

trap 'exit 0' ERR

INPUT=$(cat)

ARCHIVE_PROTECTED="${ARCHIVE_PROTECTED:-}"
[ -z "$ARCHIVE_PROTECTED" ] && exit 0

ARCHIVE_TARGET="${ARCHIVE_TARGET:-archive}"
ARCHIVE_OVERRIDE="${ARCHIVE_OVERRIDE:-ARCHIVAL-REVIEWED}"
ARCHIVE_MSG="${ARCHIVE_MSG:-Iterative analysis docs cannot be archived — each version contains unique analytical content. Override with $ARCHIVE_OVERRIDE comment.}"

COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('command', ''))
except:
    print('')
" 2>/dev/null)

# Only check git mv commands
echo "$COMMAND" | grep -q 'git mv' || exit 0

# Allow if explicitly reviewed
echo "$COMMAND" | grep -q "$ARCHIVE_OVERRIDE" && exit 0

# Block if moving from protected dirs to archive target
if echo "$COMMAND" | grep -qE "($ARCHIVE_PROTECTED).*$ARCHIVE_TARGET"; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "archive-guard" "block" "$COMMAND" 2>/dev/null || true
    echo "{\"decision\":\"block\",\"reason\":\"$ARCHIVE_MSG\"}" >&2
    exit 2
fi

exit 0
