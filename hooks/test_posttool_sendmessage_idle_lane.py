#!/usr/bin/env python3
"""Test posttool-sendmessage-idle-lane.sh.

Pins the 2026-11-03 failure: SendMessage to an idle in-process teammate returned
"Message sent to falsedup-row48's inbox" and the teammate never read it (24 min lost).
A queued send to an idle lane must say UNDELIVERED; a queued send to a busy lane says
QUEUED; a send that resumed the lane, a subagent's send and a send to main stay silent.

Run: python3 <thisfile>
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent / "posttool-sendmessage-idle-lane.sh"
CHECKS = []


def check(label, ok):
    CHECKS.append((label, ok))
    print(f"  {'✓' if ok else '✗'} {label}")


def stub_watcher(directory: Path, output: str) -> Path:
    script = directory / f"watch-{abs(hash(output))}.sh"
    script.write_text(f"#!/bin/bash\nprintf '%s' {json.dumps(output)}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def run(envelope: dict, watcher: Path) -> str:
    env = dict(os.environ, LANE_STALL_WATCH=str(watcher))
    result = subprocess.run([str(HOOK)], input=json.dumps(envelope), capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return f"rc={result.returncode}"
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def main():
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        transcript = root / "session.jsonl"
        transcript.write_text("", encoding="utf-8")
        (root / "session" / "subagents").mkdir(parents=True)
        idle = stub_watcher(root, "09:13 lane-x: BUSY -> IDLE_UNREAD (2 queued, oldest 14 min)\n")
        busy = stub_watcher(root, "")
        queued = {
            "tool_input": {"to": "lane-x", "message": "ruling"},
            "tool_response": {"success": True, "message": "Message sent to lane-x's inbox"},
            "transcript_path": str(transcript),
            "session_id": "test-session",
        }
        resumed = dict(queued, tool_response={
            "success": True,
            "message": 'Teammate "lane-x" was not running; resumed it as an in-process teammate',
        })
        to_main = dict(queued, tool_input={"to": "main", "message": "report"})
        from_subagent = dict(queued, agent_id="asubagent123")

        check("idle lane: UNDELIVERED", run(queued, idle).startswith("UNDELIVERED: lane-x is idle"))
        check("busy lane: QUEUED", run(queued, busy).startswith("QUEUED, not delivered: lane-x"))
        check("resumed lane: silent", run(resumed, idle) == "")
        check("send to main: silent", run(to_main, idle) == "")
        check("subagent's send: silent", run(from_subagent, idle) == "")

    failed = [label for label, ok in CHECKS if not ok]
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
