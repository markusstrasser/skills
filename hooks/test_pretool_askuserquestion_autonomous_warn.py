#!/usr/bin/env python3
"""Test pretool-askuserquestion-autonomous-warn.py: warn only when autonomous marker present."""
import json
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-askuserquestion-autonomous-warn.py"


def run(env: dict) -> str:
    p = subprocess.run(
        ["python3", str(HOOK)], input=json.dumps(env),
        capture_output=True, text=True, timeout=8,
    )
    assert p.returncode == 0, f"nonzero exit: {p.stderr}"
    if not p.stdout.strip():
        return ""
    return json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]


def _mk(cdir_markers):
    d = tempfile.mkdtemp()
    cdir = Path(d) / ".claude"
    cdir.mkdir()
    for m in cdir_markers:
        (cdir / m).write_text("")
    return d


def test_goal_run_fires():
    d = _mk(["goal-run"])
    assert "autonomous-run" in run({"tool_name": "AskUserQuestion", "cwd": d})


def test_goal_run_done_silent():
    d = _mk(["goal-run", "goal-done"])
    assert run({"tool_name": "AskUserQuestion", "cwd": d}) == ""


def test_loop_enforce_fires():
    d = _mk(["loop-enforce-no-question-stop"])
    assert "autonomous-run" in run({"tool_name": "AskUserQuestion", "cwd": d})


def test_session_crons_fires():
    d = _mk([])
    assert "autonomous-run" in run(
        {"tool_name": "AskUserQuestion", "cwd": d, "session_crons": [{"id": "c1"}]}
    )


def test_no_marker_silent():
    d = _mk([])
    assert run({"tool_name": "AskUserQuestion", "cwd": d}) == ""


def test_non_askuserquestion_silent():
    d = _mk(["goal-run"])
    assert run({"tool_name": "Bash", "cwd": d}) == ""


def test_empty_stdin_fail_open():
    p = subprocess.run(["python3", str(HOOK)], input="", capture_output=True, text=True, timeout=8)
    assert p.returncode == 0
    assert p.stdout.strip() == ""


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: test_pretool_askuserquestion_autonomous_warn")
