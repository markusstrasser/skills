#!/usr/bin/env python3
"""Test userprompt-disk-reclaim-suggest.py: silent above the threshold, lists candidates with
their archive commands below it, loud about a missing or stale suggestion file, rate-limited
per session, and never runs a command. Run: uv run pytest hooks/test_userprompt_disk_reclaim_suggest.py -q
"""

import json
import os
import subprocess
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "userprompt-disk-reclaim-suggest.py"


def run(
    tmp_path: Path,
    free_gb: float,
    session: str = "s1",
    event: str = "UserPromptSubmit",
    cwd: str | None = None,
    prompt: str = "hi",
):
    env = {
        **os.environ,
        "RECLAIM_CACHE_DIR": str(tmp_path),
        "RECLAIM_HOOK_STATE_DIR": str(tmp_path / "hook-state"),
        "RECLAIM_FREE_GB_OVERRIDE": str(free_gb),
    }
    payload = {
        "session_id": session,
        "hook_event_name": event,
        "prompt": prompt,
        "cwd": cwd if cwd is not None else str(tmp_path / "genomics"),
    }
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=8,
        env=env,
    )


def write_suggestions(tmp_path: Path, marker: Path, age_seconds: float = 0) -> None:
    (tmp_path / "genomics/.git").mkdir(parents=True, exist_ok=True)
    trees = tmp_path / "genomics/.claude/worktrees"
    for name in ("small", "big"):
        (trees / name).mkdir(parents=True)
    rows = [
        {
            "path": str(trees / "small"),
            "class": "stale-dirty",
            "size_bytes": 100_000_000,
            "idle_hours": 3,
            "dirty_count": 4,
            "commits_not_on_default": 0,
            "unmatched_commits": 0,
            "archive_command": f"touch {marker}",
            "candidate": True,
        },
        {
            "path": str(trees / "big"),
            "class": "unmerged",
            "size_bytes": 2_000_000_000,
            "idle_hours": 30,
            "dirty_count": 0,
            "commits_not_on_default": 3,
            "unmatched_commits": 2,
            "lock_reason": "campaign lane: do not reap until landed",
            "archive_command": f"touch {marker}",
            "candidate": True,
        },
    ]
    path = tmp_path / "worktree-suggestions.json"
    path.write_text(json.dumps({"candidates": rows, "not_candidates": [], "liveness_known": True}))
    if age_seconds:
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))


def context(proc) -> str:
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def test_silent_above_threshold(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    proc = run(tmp_path, free_gb=45)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_lists_largest_first_with_archive_command_and_runs_nothing(tmp_path):
    marker = tmp_path / "ran"
    write_suggestions(tmp_path, marker)
    proc = run(tmp_path, free_gb=12)
    ctx = context(proc)
    assert "DISK LOW: 12.0 GB free" in ctx
    assert ctx.index("worktrees/big") < ctx.index("worktrees/small")
    assert "2 with no landed match" in ctx
    assert "locked: campaign lane" in ctx
    assert f"archive: `touch {marker}`" in ctx
    assert "Nothing is removed automatically" in ctx
    assert "2 worktree reclaim candidates hold 2.1 GB" in json.loads(proc.stdout)["systemMessage"]
    assert not marker.exists()


def test_leaves_out_trees_already_removed(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    (tmp_path / "genomics/.claude/worktrees/big").rmdir()
    proc = run(tmp_path, free_gb=12)
    ctx = context(proc)
    assert "worktrees/big" not in ctx
    assert "worktrees/small" in ctx
    assert "Left out 1 listed tree already removed from disk." in ctx
    assert "1 worktree reclaim candidates hold 0.1 GB" in json.loads(proc.stdout)["systemMessage"]


def test_all_listed_trees_removed_says_so(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    for name in ("small", "big"):
        (tmp_path / "genomics/.claude/worktrees" / name).rmdir()
    ctx = context(run(tmp_path, free_gb=12))
    assert "lists no existing worktree candidates" in ctx
    assert "Left out 2 listed trees already removed from disk." in ctx


def test_session_start_echoes_event_name(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    proc = run(tmp_path, free_gb=12, event="SessionStart")
    assert json.loads(proc.stdout)["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_missing_file_is_loud(tmp_path):
    ctx = context(run(tmp_path, free_gb=12))
    assert "No reclaim suggestion file" in ctx
    assert "worktree_gc.py suggest" in ctx


def test_stale_file_is_loud(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran", age_seconds=3 * 3600)
    ctx = context(run(tmp_path, free_gb=12))
    assert "3.0 h old" in ctx
    assert "disk-guard.log" in ctx


def test_malformed_file_is_loud(tmp_path):
    (tmp_path / "worktree-suggestions.json").write_text("{not json")
    ctx = context(run(tmp_path, free_gb=12))
    assert "unreadable" in ctx


def test_rate_limited_per_session(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    assert run(tmp_path, free_gb=12).stdout
    assert run(tmp_path, free_gb=12).stdout == ""
    assert run(tmp_path, free_gb=12, session="s2").stdout


def test_repeats_when_free_space_falls_further(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    assert run(tmp_path, free_gb=15).stdout
    assert run(tmp_path, free_gb=9).stdout


def test_malformed_stdin_fails_open(tmp_path):
    env = {**os.environ, "RECLAIM_CACHE_DIR": str(tmp_path), "RECLAIM_FREE_GB_OVERRIDE": "12"}
    proc = subprocess.run(
        ["python3", str(HOOK)], input="{oops", capture_output=True, text=True, timeout=8, env=env
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_other_repo_gets_summary_only(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    (tmp_path / "skills/.git").mkdir(parents=True)
    proc = run(tmp_path, free_gb=12, cwd=str(tmp_path / "skills"))
    ctx = context(proc)
    assert ctx.startswith("DISK LOW: 12.0 GB free")
    assert "worktrees/" not in ctx and "\n" not in ctx


def test_lane_worktree_cwd_maps_to_parent_repo(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    ctx = context(run(tmp_path, free_gb=12, cwd=str(tmp_path / "genomics/.claude/worktrees/small")))
    assert "worktrees/big" in ctx


def test_no_repo_cwd_summary_once_per_band(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    outside = str(tmp_path / "nowhere")
    assert run(tmp_path, free_gb=12, cwd=outside).stdout
    assert run(tmp_path, free_gb=11, cwd=outside).stdout == ""  # same 10-15 band
    assert run(tmp_path, free_gb=9, cwd=outside).stdout  # new band


def test_full_list_repeats_only_when_candidate_set_changes(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    assert "worktrees/big" in context(run(tmp_path, free_gb=12))
    assert run(tmp_path, free_gb=12).stdout == ""
    (tmp_path / "genomics/.claude/worktrees/small").rmdir()
    assert "worktrees/big" in context(run(tmp_path, free_gb=12))


def test_harness_frames_are_skipped(tmp_path):
    write_suggestions(tmp_path, tmp_path / "ran")
    note = "<task-notification><task-id>x</task-id>done</task-notification>"
    assert run(tmp_path, free_gb=12, prompt=note).stdout == ""
    relay = "Another Claude session sent a message: status?"
    assert run(tmp_path, free_gb=12, prompt=relay).stdout == ""
    assert run(tmp_path, free_gb=12, prompt="what now?").stdout
