#!/usr/bin/env bash
# pretool-archive-guard.sh — Block git mv of analysis docs to archive dirs.
# Deploy as PreToolUse hook on Bash.
#
# Env: ARCHIVE_PROTECTED (pipe-separated regex for protected source dirs, required)
#      ARCHIVE_TARGET    (regex for target dir, default: "archive")
#      ARCHIVE_OVERRIDE  (override keyword, default: "ARCHIVAL-REVIEWED")
#      ARCHIVE_MSG       (custom block reason, optional)
#
# Exit 2 = block. Exit 0 = pass. Fails CLOSED on error (constitution P10).

trap 'echo "archive-guard: internal error at line $LINENO — blocking (fail closed)" >&2; exit 2' ERR

INPUT=$(cat)

# grep -E exits 2 on an invalid pattern; inside `if`/`||` that would read as "no match".
matches() { local rc=0; printf '%s\n' "$1" | grep -qE "$2" || rc=$?
  [ "$rc" -gt 1 ] && { echo "archive-guard: invalid pattern '$2' — blocking (fail closed)" >&2; exit 2; }
  return "$rc"; }

ARCHIVE_PROTECTED="${ARCHIVE_PROTECTED:-}"
[ -z "$ARCHIVE_PROTECTED" ] && exit 0

ARCHIVE_TARGET="${ARCHIVE_TARGET:-archive}"
ARCHIVE_OVERRIDE="${ARCHIVE_OVERRIDE:-ARCHIVAL-REVIEWED}"
ARCHIVE_MSG="${ARCHIVE_MSG:-Iterative analysis docs cannot be archived — each version contains unique analytical content. Override with $ARCHIVE_OVERRIDE comment.}"

# Cheap raw pre-check, so a missing jq or bad input blocks only `git mv` calls.
printf '%s' "$INPUT" | grep -q 'git mv' || exit 0
COMMAND=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""')

# Only check git mv commands
echo "$COMMAND" | grep -q 'git mv' || exit 0

# Allow if explicitly reviewed
echo "$COMMAND" | grep -q "$ARCHIVE_OVERRIDE" && exit 0

# Block if moving from protected dirs to archive target
if matches "$COMMAND" "($ARCHIVE_PROTECTED).*$ARCHIVE_TARGET"; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "archive-guard" "block" "$COMMAND" 2>/dev/null || true
    echo "{\"decision\":\"block\",\"reason\":\"$ARCHIVE_MSG\"}" >&2
    exit 2
fi

exit 0
