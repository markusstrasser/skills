#!/usr/bin/env bash
# precompact-log.sh — Record context snapshot before compaction.
# PreCompact hook. Side-effect only (no decision control). Fails open.
# Logs: timestamp, session, trigger, cwd, transcript size, modified files.

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c '
import sys, json, os, subprocess
from datetime import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session = data.get("session_id", "")
if not session:
    sys.exit(0)

trigger = data.get("trigger", "unknown")
cwd = data.get("cwd", "")
transcript = data.get("transcript_path", "")

t_lines = 0
if transcript and os.path.isfile(transcript):
    with open(transcript, "rb") as f:
        t_lines = sum(1 for _ in f)

modified = []
if cwd and os.path.isdir(os.path.join(cwd, ".git")):
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=cwd, capture_output=True, text=True, timeout=5
        )
        modified = [l for l in r.stdout.strip().split("\n") if l][:15]
    except Exception:
        pass

log_path = os.path.expanduser("~/.claude/compact-log.jsonl")
entry = {
    "ts": datetime.now().isoformat(timespec="seconds"),
    "session": session,
    "trigger": trigger,
    "cwd": cwd,
    "transcript_lines": t_lines,
    "modified_files": modified,
}
with open(log_path, "a") as f:
    f.write(json.dumps(entry, separators=(",", ":")) + "\n")
'

exit 0
