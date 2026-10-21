#!/usr/bin/env bash
# subagent-epistemic-gate.sh — Log subagent completions to ~/.claude/subagent-log.jsonl.
# SubagentStop command hook. Always exit 0, no output.

trap 'exit 0' ERR

INPUT=$(cat)

# Log the completion; nothing is printed or evaluated.
printf '%s' "$INPUT" | python3 -c '
import sys, json, time, os
try:
    d = json.load(sys.stdin)
    entry = json.dumps({
        "event": "subagent_stop",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "agent_type": d.get("agent_type", ""),
        "agent_id": d.get("agent_id", ""),
        "session_id": d.get("session_id", ""),
        "output_len": len(d.get("last_assistant_message", "") or ""),
        "transcript_path": d.get("agent_transcript_path", ""),
    })
    with open(os.path.expanduser("~/.claude/subagent-log.jsonl"), "a") as f:
        f.write(entry + "\n")
except Exception:
    pass
' 2>/dev/null

# No advisories. SubagentStop output lands in the finished subagent's own sidechain as a
# hook_success attachment and never reaches the parent model: 42,605 fires in 60 days
# (gov-report 2026-10-21) changed nothing. Most fires were Claude Code's internal helper
# agents (empty agent_type, ~40-char outputs) raising "SUBAGENT EMPTY". The parent reads
# the Agent tool result itself; the completion log above feeds researcher-postmortem.py.
exit 0
