#!/usr/bin/env bash
# session-stability-log.sh — instrument session_id continuity across boundaries.
#
# P4 INSTRUMENT-FIRST (genomics handoff aa683767). Before designing any
# per-session checkpoint key, we must learn EMPIRICALLY what session_id is
# stable across (a) an in-session compaction and (b) a `--resume`. The v2
# checkpoint plan assumed an exact-match session_id survives both; the Fable
# repo-axis refuted that (--resume forks a new session_id), so we measure
# instead of guessing.
#
# Wired into BOTH PreCompact and SessionStart. Reads the hook JSON from stdin,
# appends one line to ~/.claude/session-stability.jsonl. Side-effect only,
# fails open (never blocks the hook). The caller passes the event label as $1
# ("precompact" or "sessionstart").
#
# To analyze later: correlate consecutive lines — a PreCompact session_id
# followed by a SessionStart with source=compact (same id) vs source=resume
# (forked id) tells you which key survives which boundary.

trap 'exit 0' ERR

EVENT="${1:-unknown}"

cat | EVENT="$EVENT" python3 -c '
import sys, json, os
from datetime import datetime, timezone

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

line = {
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "event": os.environ.get("EVENT", "unknown"),
    "hook_event_name": data.get("hook_event_name", ""),
    "session_id": data.get("session_id", "unknown"),
    # PreCompact carries "trigger" (manual/auto); SessionStart carries "source"
    # (startup/resume/clear/compact). Capture whichever is present — together
    # they distinguish the boundary type that produced this line.
    "trigger": data.get("trigger", ""),
    "source": data.get("source", ""),
    "cwd": data.get("cwd", ""),
}

path = os.path.expanduser("~/.claude/session-stability.jsonl")
try:
    with open(path, "a") as fh:
        fh.write(json.dumps(line) + "\n")
except Exception:
    pass
' 2>/dev/null

exit 0
