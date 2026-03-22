#!/usr/bin/env bash
# Advisory stop hook: check for missing knowledge indices on modified files.
# ADVISORY ONLY (amendment A1) — logs gaps, does NOT block stop.
# Fires at Stop event.

# Fail open
trap 'exit 0' ERR

INPUT=$(cat)

# Parse session info
eval "$(echo "$INPUT" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    cwd = data.get("cwd", "")
    sid = data.get("session_id", "")
    active = data.get("stop_hook_active", False)
    if active:
        # Prevent infinite loop
        exit(0)
    if cwd:
        print(f"CWD={cwd}")
    if sid:
        print(f"SESSION={sid}")
except Exception:
    pass
')"

[ -z "$CWD" ] && exit 0

# Check if any knowledge-eligible files were modified in this session
ELIGIBLE_DIRS="analysis/entities docs/research docs/entities research decisions"
MODIFIED=$(git -C "$CWD" diff --name-only HEAD 2>/dev/null || true)

# Also check staged but uncommitted
STAGED=$(git -C "$CWD" diff --cached --name-only 2>/dev/null || true)
ALL_CHANGED=$(echo -e "$MODIFIED\n$STAGED" | sort -u | grep '\.md$' || true)

MISSING=""
for f in $ALL_CHANGED; do
    # Check if file is in an eligible directory
    ELIGIBLE=false
    for d in $ELIGIBLE_DIRS; do
        if echo "$f" | grep -q "$d/"; then
            ELIGIBLE=true
            break
        fi
    done
    [ "$ELIGIBLE" = "false" ] && continue

    FULL_PATH="$CWD/$f"
    [ -f "$FULL_PATH" ] || continue

    # Check if knowledge-index block exists
    if ! grep -q "<!-- knowledge-index" "$FULL_PATH" 2>/dev/null; then
        MISSING="$MISSING\n  $f"
    fi
done

if [ -n "$MISSING" ]; then
    # Log to pending file (advisory, not blocking)
    PENDING="$HOME/.claude/pending-knowledge-extraction.list"
    echo "# Session $SESSION $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PENDING"
    echo -e "$MISSING" >> "$PENDING"

    # Advisory context
    COUNT=$(echo -e "$MISSING" | grep -c '\S' || true)
    MSG="Knowledge index missing on $COUNT file(s):$MISSING\nConsider adding knowledge-index annotations before committing."
    ESCAPED=$(echo -e "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
    echo "{\"additionalContext\": ${ESCAPED}}"
fi

# Always allow stop (advisory, not blocking — amendment A1)
exit 0
