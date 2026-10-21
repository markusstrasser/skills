#!/usr/bin/env bash
# subagent-epistemic-gate.sh — Log subagent completions to ~/.claude/subagent-log.jsonl.
# SubagentStop command hook. Always exit 0, no output.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract agent_type, last_assistant_message, and log completion
eval "$(echo "$INPUT" | python3 -c '
import sys, json, time, os
try:
    d = json.load(sys.stdin)
    agent_type = d.get("agent_type", "")
    agent_id = d.get("agent_id", "")
    session_id = d.get("session_id", "")
    transcript_path = d.get("agent_transcript_path", "")
    msg = d.get("last_assistant_message", "")

    # Compute full length before truncation (R:P4/P12)
    msg_len = len(msg)

    # Log subagent completion to same JSONL as start events
    try:
        entry = json.dumps({
            "event": "subagent_stop",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "agent_type": agent_type,
            "agent_id": agent_id,
            "session_id": session_id,
            "output_len": msg_len,
            "transcript_path": transcript_path
        })
        logfile = os.path.expanduser("~/.claude/subagent-log.jsonl")
        with open(logfile, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass

    # Shell-safe: escape single quotes, truncate for shell use
    agent_type = agent_type.replace("'\''", "'\''\\'\'''\''")
    msg_trunc = msg[:2000].replace("'\''", "'\''\\'\'''\''")
    print(f"AGENT_TYPE='\''{ agent_type }'\''")
    print(f"MSG='\''{ msg_trunc }'\''")
    print(f"MSG_LEN={ msg_len }")
except Exception:
    print("AGENT_TYPE='\'''\''")
    print("MSG='\'''\''")
    print("MSG_LEN=0")
' 2>/dev/null)"

# No advisories. SubagentStop output lands in the finished subagent's own sidechain as a
# hook_success attachment and never reaches the parent model: 42,605 fires in 60 days
# (gov-report 2026-10-21) changed nothing. Most fires were Claude Code's internal helper
# agents (empty agent_type, ~40-char outputs) raising "SUBAGENT EMPTY". The parent reads
# the Agent tool result itself; the completion log above feeds researcher-postmortem.py.
exit 0
