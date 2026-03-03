#!/usr/bin/env bash
# verify-before-expand.sh — Advisory: run scripts before writing more
#
# Tracks scripts written but not yet run. Warns when writing a second
# script without running the first. Clears when Bash runs the script.
#
# PostToolUse:Write — records script, warns if prior script unrun
# PostToolUse:Bash  — clears script from unverified list when run
#
# State: ~/.claude/hook-state/unverified-script-$PPID (one filepath)

set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('tool_name', ''))
" 2>/dev/null) || exit 0

STATE_DIR="${HOME}/.claude/hook-state"
mkdir -p "$STATE_DIR"
STATE_FILE="${STATE_DIR}/unverified-script-${PPID}"

case "$TOOL_NAME" in
  Write)
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))
" 2>/dev/null) || exit 0

    # Only .py files in scripts/ or hooks/ directories
    [[ "$FILE_PATH" == *.py ]] || exit 0
    [[ "$FILE_PATH" == */scripts/* || "$FILE_PATH" == */hooks/* ]] || exit 0

    # Check for prior unverified script
    if [ -f "$STATE_FILE" ]; then
      PREV=$(cat "$STATE_FILE")
      if [ -n "$PREV" ] && [ "$PREV" != "$FILE_PATH" ]; then
        BASENAME=$(basename "$PREV")
        echo "⚠️  ${BASENAME} was written but never run."
        echo "   Run and verify its output before writing more scripts."
      fi
    fi

    # Record this script as unverified
    echo "$FILE_PATH" > "$STATE_FILE"
    ;;

  Bash)
    [ -f "$STATE_FILE" ] || exit 0
    UNVERIFIED=$(cat "$STATE_FILE")
    [ -n "$UNVERIFIED" ] || exit 0

    COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
" 2>/dev/null) || exit 0

    # Clear if the command references the unverified script
    BASENAME=$(basename "$UNVERIFIED")
    if echo "$COMMAND" | grep -qF "$BASENAME"; then
      rm -f "$STATE_FILE"
    fi
    ;;
esac

exit 0
