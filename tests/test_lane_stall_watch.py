"""lane-stall-watch classifies real transcript tails and prints only non-BUSY lanes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WATCH = Path(__file__).resolve().parents[1] / "bin/lane-stall-watch"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(WATCH), *args], capture_output=True, text=True,
                          check=False)


def stamp(minutes_ago: int) -> str:
    moment = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return moment.isoformat().replace("+00:00", "Z")


def transcript(directory: Path, lane: str, *rows: dict) -> None:
    path = directory / f"agent-a{lane}-0123456789abcdef.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_selftest_passes() -> None:
    result = run("--selftest")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("PASS")


def test_once_reports_each_dead_shape_and_skips_busy_lanes(tmp_path: Path) -> None:
    (tmp_path / "worktrees" / "toolstall").mkdir(parents=True)
    call = {"type": "assistant", "message": {"stop_reason": "tool_use",
                                             "content": [{"type": "tool_use", "id": "t1"}]}}
    transcript(tmp_path, "toolstall", dict(call, timestamp=stamp(9)))
    transcript(tmp_path, "overloaded", {"type": "user", "timestamp": stamp(20), "message": {}},
               {"type": "api-request", "timestamp": stamp(19)})
    transcript(tmp_path, "waiting", {"type": "assistant", "timestamp": stamp(30),
                                     "message": {"stop_reason": "end_turn"}})
    transcript(tmp_path, "thinking", {"type": "api-request", "timestamp": stamp(1)})
    result = run("--once", "--worktrees", str(tmp_path / "worktrees"), str(tmp_path))
    assert result.returncode == 0, result.stderr
    lines = sorted(line.split(" ", 1)[1] for line in result.stdout.splitlines())
    assert lines == [
        "overloaded: BUSY -> STALLED_MODEL",
        "toolstall: BUSY -> STALLED_TOOL",
        "waiting: BUSY -> IDLE",
    ]


def test_named_lanes_limit_the_watch(tmp_path: Path) -> None:
    transcript(tmp_path, "one", {"type": "user", "timestamp": stamp(20), "message": {}})
    transcript(tmp_path, "two", {"type": "user", "timestamp": stamp(20), "message": {}})
    result = run("--once", str(tmp_path), "two")
    assert [line.split(" ", 1)[1] for line in result.stdout.splitlines()] == [
        "two: BUSY -> STALLED_MODEL"
    ]


def test_missing_directory_fails_loud(tmp_path: Path) -> None:
    result = run("--once", str(tmp_path / "absent"))
    assert result.returncode == 2
    assert "no such directory" in result.stderr


def test_worktree_with_a_live_process_is_busy(tmp_path: Path) -> None:
    worktree = tmp_path / "worktrees" / "running"
    worktree.mkdir(parents=True)
    call = {"type": "assistant", "timestamp": stamp(9),
            "message": {"stop_reason": "tool_use", "content": [{"type": "tool_use"}]}}
    transcript(tmp_path, "running", call)
    # Two commands keep sh alive with the path in its argv (a lone command is exec'd away).
    holder = subprocess.Popen(["/bin/sh", "-c", f"sleep 30; : {worktree}"],
                              env={**os.environ})
    try:
        result = run("--once", "--worktrees", str(tmp_path / "worktrees"), str(tmp_path))
    finally:
        holder.kill()
        holder.wait()
    assert result.stdout == ""
