#!/usr/bin/env bash
# postcompact-verify.sh — PostCompact hook.
# Logs compaction metadata. No recovery context injection: current agents
# handle post-compaction re-orientation well enough, and repeated advisory
# text adds more friction than signal.
# Always exits 0 (advisory only).

trap 'exit 0' ERR

if [ "${CODEX_HOOK_COMPAT_SMOKE:-0}" = "1" ]; then
    exit 0
fi

LOG_FILE="$HOME/.claude/compact-log.jsonl"
INPUT=$(cat)

# Extract compaction metadata via Python
METADATA=$(echo "$INPUT" | python3 -c '
import sys, json, os

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

trigger = data.get("trigger", "unknown")
session_id = data.get("session_id", "unknown")
cwd = data.get("cwd", "")
summary_len = len(data.get("compact_summary", ""))

# Log entry
from datetime import datetime, timezone
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
log_entry = {
    "ts": ts,
    "event": "post_compact",
    "trigger": trigger,
    "session_id": session_id,
    "summary_chars": summary_len,
    "project": os.path.basename(cwd) if cwd else "unknown",
}
# Append to log
log_path = os.path.expanduser("~/.claude/compact-log.jsonl")
with open(log_path, "a") as f:
    f.write(json.dumps(log_entry) + "\n")
' 2>/dev/null)

exit 0
