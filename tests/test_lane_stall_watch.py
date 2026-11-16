"""lane-stall-watch classifies real transcript tails and prints only non-BUSY lanes."""

from __future__ import annotations

import json
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


def bash_call(minutes_ago: int, **arguments: object) -> dict:
    block = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "x", **arguments}}
    return {"type": "assistant", "timestamp": stamp(minutes_ago),
            "message": {"stop_reason": "tool_use", "content": [block]}}


def transcript(directory: Path, lane: str, *rows: dict) -> None:
    path = directory / f"agent-a{lane}-0123456789abcdef.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_selftest_passes() -> None:
    result = run("--selftest")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("PASS")


def test_once_reports_each_dead_shape_and_skips_busy_lanes(tmp_path: Path) -> None:
    transcript(tmp_path, "toolstall", bash_call(9))
    transcript(tmp_path, "overloaded", {"type": "user", "timestamp": stamp(20), "message": {}},
               {"type": "api-request", "timestamp": stamp(19)})
    transcript(tmp_path, "waiting", {"type": "assistant", "timestamp": stamp(30),
                                     "message": {"stop_reason": "end_turn"}})
    transcript(tmp_path, "thinking", {"type": "api-request", "timestamp": stamp(1)})
    # A long Bash call inside its own declared timeout is work, not a stall (2026-10-27
    # negatives-hubs: a 540 s pytest batch run from a scratchpad script).
    transcript(tmp_path, "longcall", bash_call(7, timeout=540_000))
    result = run("--once", str(tmp_path))
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


def test_worktree_agent_is_named_by_its_meta_file(tmp_path: Path) -> None:
    # An agent started in its own worktree writes agent-a<id>.jsonl: the file name carries no
    # lane name, the sibling meta file does (2026-11-17: `trainer-2` was refused by name twice
    # in one night and had to be watched by its id).
    row = {"type": "user", "timestamp": stamp(20), "message": {}}
    (tmp_path / "agent-aacc71e64470e255e.jsonl").write_text(json.dumps(row) + "\n")
    (tmp_path / "agent-aacc71e64470e255e.meta.json").write_text(json.dumps({"name": "trainer-2"}))
    transcript(tmp_path, "other", row)
    for spelling in ("trainer-2", "acc71e64470e255e", "aacc71e64470e255e"):
        result = run("--once", str(tmp_path), spelling)
        assert result.returncode == 0, (spelling, result.stderr)
        assert [line.split(" ", 1)[1] for line in result.stdout.splitlines()] == [
            "trainer-2: BUSY -> STALLED_MODEL"
        ], spelling
    # With no lane named, the watch over recent transcripts labels it by its name too.
    result = run("--once", str(tmp_path))
    assert sorted(line.split(" ", 1)[1] for line in result.stdout.splitlines()) == [
        "other: BUSY -> STALLED_MODEL",
        "trainer-2: BUSY -> STALLED_MODEL",
    ]
    # A name that neither a file name nor a meta file gives still fails loud.
    result = run("--once", str(tmp_path), "trainer-3")
    assert result.returncode == 2
    assert "trainer-3" in result.stderr
