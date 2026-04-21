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
eval "$(echo "$INPUT" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    sid = data.get("session_id") or data.get("sessionId") or data.get("id") or ""
    cwd = data.get("cwd") or data.get("working_directory") or data.get("work_dir") or ""
    if sid:
        print(f"SID={sid}")
    if cwd:
        print(f"CWD={cwd}")
except Exception:
    pass
' 2>/dev/null)"

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
