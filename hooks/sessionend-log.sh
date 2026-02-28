#!/usr/bin/env bash
# sessionend-log.sh — Log session end events for forensics.
# SessionEnd hook. Side-effect only (no decision control). Fails open.
# Logs: timestamp, session, reason, cwd, transcript size.

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c '
import sys, json, os
from datetime import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session = data.get("session_id", "")
if not session:
    sys.exit(0)

reason = data.get("reason", "unknown")
cwd = data.get("cwd", "")
transcript = data.get("transcript_path", "")

t_lines = 0
if transcript and os.path.isfile(transcript):
    with open(transcript, "rb") as f:
        t_lines = sum(1 for _ in f)

log_path = os.path.expanduser("~/.claude/session-log.jsonl")
entry = {
    "ts": datetime.now().isoformat(timespec="seconds"),
    "session": session,
    "reason": reason,
    "cwd": cwd,
    "transcript_lines": t_lines,
}
with open(log_path, "a") as f:
    f.write(json.dumps(entry, separators=(",", ":")) + "\n")
'

exit 0
