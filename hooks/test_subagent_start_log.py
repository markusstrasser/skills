#!/usr/bin/env python3
"""Regression tests for subagent-start-log.sh.

Until 2026-09-25 the hook ran its Python through `eval "$(...)"`, so the JSON meant for Claude
Code was executed as shell code: every subagent start logged
`line 10: {additionalContext:: command not found` and no context reached any subagent.
These tests run the hook as Claude Code does (event JSON on stdin) with HOME pointed at a
temporary directory, so the real ~/.claude/subagent-log.jsonl is untouched.
"""
import json
import os
import pathlib
import subprocess
import tempfile

HOOK = pathlib.Path(__file__).resolve().parent / "subagent-start-log.sh"


def run(event: dict | str, home: pathlib.Path) -> subprocess.CompletedProcess:
    payload = event if isinstance(event, str) else json.dumps(event)
    env = dict(os.environ, HOME=str(home))
    return subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True, env=env)


def project_with_overview(root: pathlib.Path) -> pathlib.Path:
    proj = root / "proj"
    (proj / ".claude" / "overviews").mkdir(parents=True)
    (proj / ".claude" / "overviews" / "source-overview.md").write_text(
        "# Source\n<!-- INDEX\nsrc/app.py — entry point\nsrc/db.py — storage\n-->\nbody\n")
    return proj


def test_explore_gets_overview_context_as_hook_json():
    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t) / "home"
        (home / ".claude").mkdir(parents=True)
        proj = project_with_overview(pathlib.Path(t))
        r = run({"agent_type": "Explore", "agent_id": "a1", "session_id": "s1", "cwd": str(proj)}, home)
        assert r.returncode == 0
        assert "command not found" not in r.stderr
        out = json.loads(r.stdout)
        spec = out["hookSpecificOutput"]
        assert spec["hookEventName"] == "SubagentStart"
        assert spec["additionalContext"].startswith("CODEBASE STRUCTURE:\n## source\n")
        assert "src/db.py — storage" in spec["additionalContext"]
        log = (home / ".claude" / "subagent-log.jsonl").read_text().splitlines()
        assert json.loads(log[-1])["agent_type"] == "Explore"


def test_researcher_is_logged_without_the_stale_budget():
    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t) / "home"
        (home / ".claude").mkdir(parents=True)
        r = run({"agent_type": "researcher", "agent_id": "a2", "session_id": "s1", "cwd": t}, home)
        assert r.returncode == 0
        assert r.stdout == "" and r.stderr == ""
        log = (home / ".claude" / "subagent-log.jsonl").read_text().splitlines()
        assert json.loads(log[-1])["agent_id"] == "a2"


def test_malformed_input_is_silent():
    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t) / "home"
        (home / ".claude").mkdir(parents=True)
        r = run("not json", home)
        assert r.returncode == 0
        assert r.stdout == "" and r.stderr == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"✓ {name}")
