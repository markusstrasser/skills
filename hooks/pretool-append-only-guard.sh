#!/usr/bin/env bash
# pretool-append-only-guard.sh — Block edits that shrink protected files.
# Deploy as PreToolUse hook on Write|Edit.
#
# Env: APPENDONLY_PATHS (pipe-separated regex patterns matching protected paths, required)
# Env: APPENDONLY_MSG  (custom block reason, optional)
#
# Logic:
#   Write to existing file: block if new content has fewer lines than existing
#   Edit: block if new_string is shorter than old_string AND old content not preserved
#   New files: always allowed
#
# Exit 2 = block. Exit 0 = pass. Fails open on error.

trap 'exit 0' ERR

INPUT=$(cat)

APPENDONLY_PATHS="${APPENDONLY_PATHS:-}"
[ -z "$APPENDONLY_PATHS" ] && exit 0

APPENDONLY_MSG="${APPENDONLY_MSG:-Protected file is append-only. Cannot shrink content. Use Edit to append.}"

# Extract file path
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')
[ -z "$FPATH" ] && exit 0

# Check if path matches any protected pattern
echo "$FPATH" | grep -qE "$APPENDONLY_PATHS" || exit 0

TOOL_NAME=$(echo "$INPUT" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"tool_name"[[:space:]]*:[[:space:]]*"//;s/"//')

if [ "$TOOL_NAME" = "Write" ]; then
    # New file — allow
    [ ! -f "$FPATH" ] && exit 0

    EXISTING_LINES=$(wc -l < "$FPATH" 2>/dev/null || echo 0)
    # Disable trap so Python exit code propagates
    trap - ERR
    NEW_LINES=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('content', '').count(chr(10)))
except:
    print(0)
" 2>/dev/null)
    trap 'exit 0' ERR

    if [ "$NEW_LINES" -lt "$EXISTING_LINES" ]; then
        ~/Projects/skills/hooks/hook-trigger-log.sh "append-only-guard" "block" "$FPATH" 2>/dev/null || true
        echo "{\"decision\":\"block\",\"reason\":\"$APPENDONLY_MSG\"}" >&2
        exit 2
    fi
fi

if [ "$TOOL_NAME" = "Edit" ]; then
    trap - ERR
    RESULT=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
old = d.get('old_string', '')
new = d.get('new_string', '')
if len(new.strip()) < len(old.strip()) and old.strip() not in new:
    print('block')
else:
    print('allow')
" 2>/dev/null)
    trap 'exit 0' ERR

    if [ "$RESULT" = "block" ]; then
        ~/Projects/skills/hooks/hook-trigger-log.sh "append-only-guard" "block" "$FPATH" 2>/dev/null || true
        echo "{\"decision\":\"block\",\"reason\":\"$APPENDONLY_MSG\"}" >&2
        exit 2
    fi
fi

exit 0
