#!/usr/bin/env bash
# sessionend-log.sh — Log session end events + flight receipt for forensics.
# SessionEnd hook. Side-effect only (no decision control). Fails open.
# Logs: timestamp, session, reason, cwd, transcript size, cost (from cockpit state).

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

# Read cockpit state persisted by status line
cockpit = {}
cockpit_path = f"/tmp/claude-cockpit-{session}"
if os.path.isfile(cockpit_path):
    try:
        with open(cockpit_path) as f:
            cockpit = json.load(f)
        os.unlink(cockpit_path)  # clean up
    except Exception:
        pass

# Extract project name from cwd
project = os.path.basename(cwd) if cwd else ""

ts = datetime.now().isoformat(timespec="seconds")

# --- Session log (existing format, backwards compatible) ---
log_entry = {
    "ts": ts,
    "session": session,
    "reason": reason,
    "cwd": cwd,
    "transcript_lines": t_lines,
}
log_path = os.path.expanduser("~/.claude/session-log.jsonl")
with open(log_path, "a") as f:
    f.write(json.dumps(log_entry, separators=(",", ":")) + "\n")

# --- Flight receipt (enriched with cockpit data) ---
duration_ms = int(cockpit.get("duration_ms", 0))
mins = round(duration_ms / 60000, 1) if duration_ms else 0

receipt = {
    "ts": ts,
    "session": session,
    "project": project,
    "model": cockpit.get("model", "?"),
    "branch": cockpit.get("branch", "?"),
    "reason": reason,
    "duration_min": mins,
    "cost_usd": float(cockpit.get("cost", 0)),
    "context_pct": int(cockpit.get("context_pct", 0)),
    "lines_added": int(cockpit.get("lines_added", 0)),
    "lines_removed": int(cockpit.get("lines_removed", 0)),
    "transcript_lines": t_lines,
}
receipt_path = os.path.expanduser("~/.claude/session-receipts.jsonl")
with open(receipt_path, "a") as f:
    f.write(json.dumps(receipt, separators=(",", ":")) + "\n")
'

exit 0
