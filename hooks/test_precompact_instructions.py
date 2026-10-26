#!/usr/bin/env python3
"""Tests for precompact-instructions.py — run: uv run python3 test_precompact_instructions.py"""
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

HOOK = Path(__file__).parent / "precompact-instructions.py"
CONTRACT = "Re-read before relying on details"


def contract_only(out: str) -> bool:
    return CONTRACT in out and "Active skill arcs" not in out


def run_hook(
    payload: dict,
    log_lines: Sequence[dict | str],
    goal_run: bool = False,
    brief_name: str = "",
) -> str:
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        (home / ".claude").mkdir()
        log = home / ".claude" / "skill-triggers.jsonl"
        log.write_text(
            "\n".join(r if isinstance(r, str) else json.dumps(r) for r in log_lines)
        )
        cwd = home / "proj"
        (cwd / ".claude").mkdir(parents=True)
        if goal_run:
            (cwd / ".claude" / "goal-run").write_text("1")
        if brief_name:
            (cwd / ".claude" / brief_name).write_text("# hand-written brief\n")
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
    assert "/decide" in out and "re-attaches" in out, out
    ok += 1
    # 2. other session's invocations -> contract only
    out = run_hook({"session_id": "s1"}, [row("decide", "s2")])
    assert contract_only(out), out
    ok += 1
    # 3. no log rows -> contract only
    out = run_hook({"session_id": "s1"}, [])
    assert contract_only(out), out
    ok += 1
    # 4. goal-run marker -> still emits contract + arc (binary joins hook outputs)
    out = run_hook({"session_id": "s1"}, [row("decide", "s1")], goal_run=True)
    assert "/decide" in out and "Re-read before relying on details" in out, out
    ok += 1
    # 5. stale invocation (>12h) -> contract only
    out = run_hook({"session_id": "s1"}, [row("decide", "s1", hours_ago=20)])
    assert contract_only(out), out
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
    # 8. corrupt log fragments (non-dict JSON scalars + raw prose) -> skipped,
    #    good rows still fire (regression: 2026-07-06 compaction crash on "1." -> 1.0)
    out = run_hook(
        {"session_id": "s1"},
        [row("decide", "s1"), "1.", "Adversarial", "[1,2]", "null", '"str"'],
    )
    assert "/decide" in out, out
    ok += 1
    # 9. the re-read list names THIS session's checkpoint, never the shared checkpoint.md
    sid = "aaaaaaaa-1111-4111-8111-111111111111"
    out = run_hook({"session_id": sid}, [])
    assert "/.claude/checkpoint-auto-aaaaaaaa.md" in out, out
    assert "checkpoint.md" not in out and "hand-written brief" not in out, out
    ok += 1
    # 10. the session's own hand-written brief is named only when it exists
    out = run_hook({"session_id": sid}, [], brief_name="checkpoint-aaaaaaaa.md")
    assert "hand-written brief" in out and "/.claude/checkpoint-aaaaaaaa.md" in out, out
    ok += 1
    # 11. no usable session id -> the writer writes no checkpoint, so none is named
    out = run_hook({"session_id": ""}, [])
    assert contract_only(out) and "checkpoint" not in out, out
    ok += 1
    print(f"OK — {ok}/11 cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
