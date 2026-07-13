#!/usr/bin/env python3
"""Tests for reap_stale_trackers — the /tmp tracker-leak reaper.

The safety contract is the point of these tests: a tracker grants a session ownership of
files it edited, so reaping a LIVE session's tracker would make its own files look
"foreign" to the commit guard and block it. Every "preserved" test below is a guard
against that.

The final test is a POSITIVE CONTROL on the wiring: it invokes the real
pretool-universal-dispatch.py hook and asserts a stale tracker actually disappears. Without
it, an ImportError inside the hook's `except Exception: pass` would leave the reaper
permanently dead and silent — the exact failure class this whole change exists to fix.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reap_stale_trackers import MIN_AGE_S, maybe_reap, reap  # noqa: E402

HOOK = Path(__file__).resolve().parent / "pretool-universal-dispatch.py"
OLD = MIN_AGE_S + 600  # comfortably past the age floor


def _write(directory: Path, name: str, *, age_s: float = 0.0) -> Path:
    path = directory / name
    path.write_text("scripts/whatever.py\n", encoding="utf-8")
    if age_s:
        stamp = time.time() - age_s
        os.utime(path, (stamp, stamp))
    return path


def _dead_pid() -> int:
    """A PID that is definitely not running (spawn a trivial child, reap it)."""
    proc = subprocess.Popen(["true"])
    proc.wait()
    return proc.pid


def test_reaps_dead_pid_tracker_past_age_floor(tmp_path: Path) -> None:
    stale = _write(tmp_path, f"claude-write-intent-abc-{_dead_pid()}.txt", age_s=OLD)
    assert reap(str(tmp_path)) == 1
    assert not stale.exists()


def test_preserves_live_pid_tracker(tmp_path: Path) -> None:
    """Safety rule 1 — a live session must never lose its ownership claims."""
    live = _write(tmp_path, f"claude-write-intent-abc-{os.getpid()}.txt", age_s=OLD)
    assert reap(str(tmp_path)) == 0
    assert live.exists()


def test_preserves_recent_tracker_even_if_pid_is_dead(tmp_path: Path) -> None:
    """Safety rule 2 — the consuming guard trusts a 30-min window; we floor at 60 min."""
    recent = _write(tmp_path, f"claude-write-intent-abc-{_dead_pid()}.txt", age_s=60)
    assert reap(str(tmp_path)) == 0
    assert recent.exists()


def test_preserves_tracker_with_no_provable_owner(tmp_path: Path) -> None:
    """Safety rule 3 — no PID suffix means no provable owner; keep it."""
    orphan = _write(tmp_path, "claude-session-touched-no-ppid.txt", age_s=OLD)
    assert reap(str(tmp_path)) == 0
    assert orphan.exists()


def test_ignores_non_claude_files(tmp_path: Path) -> None:
    bystander = _write(tmp_path, f"unrelated-{_dead_pid()}.txt", age_s=OLD)
    assert reap(str(tmp_path)) == 0
    assert bystander.exists()


def test_throttle_skips_second_scan(tmp_path: Path) -> None:
    _write(tmp_path, f"claude-write-intent-abc-{_dead_pid()}.txt", age_s=OLD)
    assert maybe_reap(str(tmp_path)) == 1
    # Second call inside the throttle window must be a no-op (the hot-path guarantee).
    _write(tmp_path, f"claude-write-intent-def-{_dead_pid()}.txt", age_s=OLD)
    assert maybe_reap(str(tmp_path)) == 0


def test_hook_wiring_positive_control(tmp_path: Path) -> None:
    """POSITIVE CONTROL: the real hook must actually reap. Catches a silent ImportError.

    The hook swallows exceptions to fail open, so a broken import would make the reaper a
    permanent no-op with zero signal. This proves it fires for real.
    """
    stale = _write(tmp_path, f"claude-bash-snapshot-xyz-{_dead_pid()}.txt", age_s=OLD)
    env = {**os.environ, "CLAUDE_HOOK_STATE_DIR": str(tmp_path)}
    envelope = json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
    subprocess.run(
        [sys.executable, str(HOOK)],
        input=envelope,
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
        check=False,  # the hook may exit 0 or 2; we only care that it reaped
    )
    assert not stale.exists(), "hook did not reap — the reaper is silently dead"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
