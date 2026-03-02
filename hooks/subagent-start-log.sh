#!/usr/bin/env bash
# subagent-start-log.sh — Log every subagent spawn to ~/.claude/subagent-log.jsonl
# SubagentStart command hook. No blocking (exit 0 always).

trap 'exit 0' ERR

INPUT=$(cat)

# Parse fields from event JSON via Python (matches epistemic-gate pattern)
eval "$(echo "$INPUT" | python3 -c '
import sys, json, time, os
try:
    d = json.load(sys.stdin)
    agent_type = d.get("agent_type", "unknown")
    agent_id = d.get("agent_id", "")
    session_id = d.get("session_id", "")
    cwd = d.get("cwd", "")
    project = os.path.basename(cwd) if cwd else ""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    entry = json.dumps({
        "event": "subagent_start",
        "ts": ts,
        "agent_type": agent_type,
        "agent_id": agent_id,
        "session_id": session_id,
        "project": project,
        "cwd": cwd
    })

    logfile = os.path.expanduser("~/.claude/subagent-log.jsonl")
    with open(logfile, "a") as f:
        f.write(entry + "\n")
except Exception:
    pass
' 2>/dev/null)"

exit 0
