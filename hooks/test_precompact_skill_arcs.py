#!/usr/bin/env python3
"""Tests for precompact-skill-arcs.py — run: uv run python3 test_precompact_skill_arcs.py"""
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOK = Path(__file__).parent / "precompact-skill-arcs.py"


def run_hook(payload: dict, log_lines: list[dict], goal_run: bool = False) -> str:
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        (home / ".claude").mkdir()
        log = home / ".claude" / "skill-triggers.jsonl"
        log.write_text("\n".join(json.dumps(r) for r in log_lines))
        cwd = home / "proj"
        (cwd / ".claude").mkdir(parents=True)
        if goal_run:
            (cwd / ".claude" / "goal-run").write_text("1")
        payload = {**payload, "cwd": str(cwd)}
        out = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        )
        assert out.returncode == 0, out.stderr
        return out.stdout


def row(skill, session, hours_ago=0, args=""):
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "ts": ts,
        "event": "skill_invoke",
        "skill": skill,
        "args": args,
        "session": session,
        "project": "x",
    }


def main() -> int:
    ok = 0
    # 1. session with an invoked skill -> instructions name it
    out = run_hook({"session_id": "s1"}, [row("decide", "s1", args="schema fork")])
    assert "/decide" in out and "re-invoke" in out, out
    ok += 1
    # 2. other session's invocations -> silent
    out = run_hook({"session_id": "s1"}, [row("decide", "s2")])
    assert out == "", out
    ok += 1
    # 3. no log rows -> silent
    out = run_hook({"session_id": "s1"}, [])
    assert out == "", out
    ok += 1
    # 4. goal-run marker -> defers (silent) even with active arc
    out = run_hook({"session_id": "s1"}, [row("decide", "s1")], goal_run=True)
    assert out == "", out
    ok += 1
    # 5. stale invocation (>12h) -> silent
    out = run_hook({"session_id": "s1"}, [row("decide", "s1", hours_ago=20)])
    assert out == "", out
    ok += 1
    # 6. dedup + cap: 5 skills -> newest 3, one mention each
    rows = [row(s, "s1", hours_ago=h) for h, s in enumerate(["a", "b", "c", "d", "e"])]
    out = run_hook({"session_id": "s1"}, rows)
    assert "/a" in out and "/b" in out and "/c" in out and "/d" not in out, out
    ok += 1
    # 7. non-arc rows mixed in -> ignored, good rows still fire
    out = run_hook(
        {"session_id": "s1"},
        [row("decide", "s1")] + [{"garbage": True}],
    )
    assert "/decide" in out, out
    ok += 1
    print(f"OK — {ok}/7 cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
