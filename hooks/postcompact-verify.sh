#!/usr/bin/env bash
# postcompact-verify.sh — PostCompact hook.
# Logs compaction metadata and injects post-compaction recovery context.
# Always exits 0 (advisory only).

trap 'exit 0' ERR

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

# Emit additionalContext for recovery
checkpoint_path = os.path.join(cwd, ".claude", "checkpoint.md") if cwd else ""
has_checkpoint = os.path.isfile(checkpoint_path) if checkpoint_path else False

context = "POST-COMPACTION RECOVERY:\n"
context += "1. Run `git log --oneline -10` to verify any claimed completed work actually exists.\n"
context += "2. Compaction summaries can hallucinate completed work — trust git, not the summary.\n"
if has_checkpoint:
    context += f"3. Read {checkpoint_path} for pre-compaction state and pending tasks.\n"
else:
    context += "3. No checkpoint.md found — reconstruct state from git log and file state.\n"
context += "4. Do NOT ask the user for context — re-orient from checkpoint + git state.\n"

output = {"additionalContext": context}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$METADATA" ]]; then
    echo "$METADATA"
fi

exit 0
