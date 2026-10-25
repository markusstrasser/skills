#!/usr/bin/env python3
"""Regression tests for posttool-subagent-output-check.sh.

Until 2026-10-26 the hook ran on background launches too: PostToolUse:Agent fires when
the launch returns, before the agent has written anything, so every background dispatch
that promised a file drew "SUBAGENT OUTPUT MISSING ... verify ... or redo the task
directly" (2,868 MISSING fires logged). HOME points at a temporary directory so the real
trigger log is untouched.
"""
import json
import os
import pathlib
import subprocess
import tempfile

HOOK = pathlib.Path(__file__).resolve().parent / "posttool-subagent-output-check.sh"


def run(event: dict, home: pathlib.Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, HOME=str(home))
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True, env=env)


def event(out_path: pathlib.Path, response: dict) -> dict:
    return {"tool_input": {"prompt": f"Write results to {out_path}", "subagent_type": "general-purpose"},
            "tool_response": response}


def test_background_launch_is_silent():
    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t)
        r = run(event(home / "missing.md", {"isAsync": True, "status": "async_launched"}), home)
        assert r.returncode == 0
        assert r.stdout.strip() == "", r.stdout


def test_finished_agent_without_its_file_warns():
    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t)
        r = run(event(home / "missing.md", {"status": "completed", "content": []}), home)
        assert r.returncode == 0
        assert "SUBAGENT OUTPUT MISSING" in json.loads(r.stdout)["additionalContext"]


def test_finished_agent_with_its_file_is_silent():
    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t)
        out = home / "done.md"
        out.write_text("**Verdict:** ok\n")
        r = run(event(out, {"status": "completed", "content": []}), home)
        assert r.returncode == 0
        assert r.stdout.strip() == "", r.stdout


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK")
