#!/usr/bin/env bash
# kimi-session-start.sh — SessionStart hook for Kimi CLI.
# Persists "kimi:<session_id>" to .claude/current-session-id so that
# prepare-commit-msg appends Session-ID: kimi:<uuid> to commits made
# from Kimi sessions.
#
# Also logs the first few stdin payloads to /tmp/kimi-hook-probe.log
# so we can verify the JSON shape matches Claude's contract. Remove the
# probe once confirmed.
#
# Fails open on any error (exit 0).

trap 'exit 0' ERR

INPUT=$(cat)

# Debug probe: capture up to 5 invocations for protocol verification.
PROBE_LOG="/tmp/kimi-hook-probe.log"
PROBE_COUNT_FILE="/tmp/kimi-hook-probe.count"
COUNT=$(cat "$PROBE_COUNT_FILE" 2>/dev/null || echo 0)
if [ "$COUNT" -lt 5 ]; then
    {
        echo "--- $(date -u +%Y-%m-%dT%H:%M:%SZ) SessionStart ---"
        echo "$INPUT" | python3 -m json.tool 2>/dev/null || echo "$INPUT"
        echo ""
    } >> "$PROBE_LOG" 2>/dev/null
    echo $((COUNT + 1)) > "$PROBE_COUNT_FILE" 2>/dev/null
fi

# Extract session_id and cwd — try Claude's shape first, fall back to
# common alternates Kimi might use.
SID=$(printf '%s' "$INPUT" | jq -r 'first((.session_id, .sessionId, .id) | select(. != null and . != "" and . != false)) // ""' 2>/dev/null || echo "")
CWD=$(printf '%s' "$INPUT" | jq -r 'first((.cwd, .working_directory, .work_dir) | select(. != null and . != "" and . != false)) // ""' 2>/dev/null || echo "")

[ -z "$SID" ] && exit 0

TAGGED="kimi:$SID"

# Write to project-level .claude/current-session-id if cwd is given and
# writable; otherwise fall back to global.
if [ -n "$CWD" ] && [ -d "$CWD" ]; then
    mkdir -p "$CWD/.claude" 2>/dev/null
    echo "$TAGGED" > "$CWD/.claude/current-session-id" 2>/dev/null || \
        echo "$TAGGED" > "$HOME/.claude/current-session-id" 2>/dev/null
else
    echo "$TAGGED" > "$HOME/.claude/current-session-id" 2>/dev/null
fi

exit 0
