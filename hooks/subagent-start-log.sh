#!/usr/bin/env bash
# subagent-start-log.sh — Log every subagent spawn to ~/.claude/subagent-log.jsonl
# SubagentStart command hook. No blocking (exit 0 always).
#
# The Python below writes the log line itself and prints at most one JSON object to the hook's
# stdout: hookSpecificOutput.additionalContext with the project's overview INDEX blocks for
# Explore and general-purpose subagents. Until 2026-09-25 that JSON was captured by
# `eval "$(...)"` and run as shell code ("{additionalContext:: command not found" on every
# subagent start), so no context ever reached a subagent. The researcher's old "25 turns max,
# synthesize by turn 18" injection was dropped with the fix: its turn cap (40) and write-first
# protocol live in ~/.claude/agents/researcher.md. Regression test: test_subagent_start_log.py.

trap 'exit 0' ERR

python3 -c '
import sys, json, time, os, re
try:
    d = json.load(sys.stdin)
    agent_type = d.get("agent_type", "unknown")
    cwd = d.get("cwd", "")
    entry = json.dumps({
        "event": "subagent_start",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "agent_type": agent_type,
        "agent_id": d.get("agent_id", ""),
        "session_id": d.get("session_id", ""),
        "project": os.path.basename(cwd) if cwd else "",
        "cwd": cwd,
    })
    with open(os.path.expanduser("~/.claude/subagent-log.jsonl"), "a") as f:
        f.write(entry + "\n")

    # Overview INDEX blocks as additionalContext for Explore and general-purpose subagents.
    if agent_type in ("Explore", "general-purpose") and cwd:
        overview_dir = os.path.join(cwd, ".claude", "overviews")
        blocks = []
        if os.path.isdir(overview_dir):
            for fname in sorted(os.listdir(overview_dir)):
                if not fname.endswith("-overview.md"):
                    continue
                text = open(os.path.join(overview_dir, fname)).read()
                m = re.search(r"<!-- INDEX\b(.*?)-->", text, re.DOTALL)
                if m:
                    lines = m.group(1).strip().split("\n")
                    block = "\n".join(lines[:60]) + ("\n... (truncated)" if len(lines) > 60 else "")
                    name = fname[: -len("-overview.md")]
                    blocks.append(f"## {name}\n{block}")
        if blocks:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": "CODEBASE STRUCTURE:\n" + "\n\n".join(blocks),
            }}))
except Exception:
    pass
' 2>/dev/null

exit 0
