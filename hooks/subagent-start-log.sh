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

    # Emit overview INDEX as additionalContext for Explore subagents
    if agent_type in ("Explore", "general-purpose"):
        overview_dir = os.path.join(cwd, ".claude", "overviews")
        if os.path.isdir(overview_dir):
            import re
            blocks = []
            for fname in sorted(os.listdir(overview_dir)):
                if not fname.endswith("-overview.md"):
                    continue
                fpath = os.path.join(overview_dir, fname)
                text = open(fpath).read()
                m = re.search(r"<!-- INDEX\b(.*?)-->", text, re.DOTALL)
                if m:
                    name = fname.replace("-overview.md", "")
                    block = m.group(1).strip()
                    lines = block.split("\n")
                    if len(lines) > 60:
                        block = "\n".join(lines[:60]) + "\n... (truncated)"
                    blocks.append(f"## {name}\n{block}")
            if blocks:
                ctx = "CODEBASE STRUCTURE:\\n" + "\\n\\n".join(blocks)
                print(json.dumps({"additionalContext": ctx}))
    # Inject synthesis budget reminder for researcher subagents
    if agent_type == "researcher":
        ctx = "RESEARCHER BUDGET: You have 25 turns max. By turn 18, you MUST begin writing your synthesis. A partial synthesis with [UNVERIFIED] tags beats no output. Your stop hook will reject empty output."
        print(json.dumps({"additionalContext": ctx}))
except Exception:
    pass
' 2>/dev/null)"

exit 0
