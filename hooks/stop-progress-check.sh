#!/usr/bin/env bash
# stop-progress-check.sh — Stop hook: shadow-mode stagnation detection.
# Fires at session end. Checks if high tool-call count with zero commits
# indicates a stagnant session (lots of work, no persistent output).
#
# SHADOW MODE: Logs would-fire events to ~/.claude/stagnation-shadow.jsonl
# but never returns advisory output. Enable after 2-week precision check.
#
# Env: CLAUDE_SESSION_ID, CLAUDE_CWD

trap 'exit 0' ERR

INPUT=$(cat)

python3 -c '
import sys, json, subprocess, os
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/stagnation-shadow.jsonl")
TRIGGER_LOG = os.path.expanduser("~/.claude/hook-triggers.jsonl")
TOOL_CALL_THRESHOLD = 40

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

session_id = os.environ.get("CLAUDE_SESSION_ID", "")
if not session_id:
    sys.exit(0)

cwd = os.environ.get("CLAUDE_CWD", data.get("cwd", ""))
project = os.path.basename(cwd) if cwd else "unknown"

# Count tool calls for this session from hook-triggers.jsonl
tool_calls = 0
try:
    with open(TRIGGER_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if session_id in line:
                tool_calls += 1
except (OSError, FileNotFoundError):
    pass

# Count recent commits in the working directory
commits = 0
if cwd and os.path.isdir(os.path.join(cwd, ".git")):
    try:
        result = subprocess.run(
            ["git", "log", "--since=1 hour ago", "--oneline"],
            cwd=cwd, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            commits = len([l for l in result.stdout.strip().split("\n") if l.strip()])
    except Exception:
        pass

would_fire = tool_calls > TOOL_CALL_THRESHOLD and commits == 0

# Always log to shadow file for precision tracking
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
entry = {
    "ts": ts,
    "event": "stagnation_shadow",
    "session": session_id,
    "project": project,
    "tool_calls": tool_calls,
    "commits": commits,
    "would_fire": would_fire,
}
try:
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
except OSError:
    pass

# Shadow mode: never output anything, always exit 0
' <<< "$INPUT" 2>/dev/null

exit 0
