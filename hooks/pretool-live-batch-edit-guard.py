#!/usr/bin/env python3
"""pretool-live-batch-edit-guard.py — no edits to genomics MAIN's launch source mid-row.

PreToolUse (Write|Edit|NotebookEdit). Blocks an edit to the genomics main checkout's
scripts/ or config/ while a `just drive-batch` row is in flight (a batch dir's
in-flight.json names a live driver pid). Every native launch seals those two roots
from HEAD and refuses a dirty tree (`SOURCE_BUNDLE_ROOTS`, DirtyGitSourceError in
genomics scripts/genome_kernel_source_bundle.py), so a mid-row edit kills the row.

Why: 2026-09-22, twice in one evening. An in-place M322 fix on main killed
syn7sr clinical_report, and a peer session's model-pin sweep killed family_cascade
after 2.8 h plus the next row (genetic_load) and refused a landing.

Allowed: worktrees (.claude/worktrees/… resolve outside scripts/ and config/),
any other repo or path, and a batch parked at PAUSE (no in-flight.json): pause,
wait for the row to end, edit + commit, then lift PAUSE. Override for an
emergency: GENOMICS_LIVE_BATCH_EDIT_OK=1 in the session environment.

Known gap (accepted): Bash-driven edits (sed -i, redirects, scripts) bypass this
Write|Edit guard, like pretool-subagent-settings-guard.py.

Fail-open on any internal error.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# The two LIVE_BATCH_GUARD_* variables exist for hermetic tests only.
REPO = Path(os.environ.get("LIVE_BATCH_GUARD_REPO", "/Users/alien/Projects/genomics"))
DRIVER_MARK = os.environ.get("LIVE_BATCH_GUARD_DRIVER_MARK", "drive_batch.py")
SOURCE_ROOTS = ("scripts", "config")


def _driver_alive(pid: int) -> bool:
    # Dead batches leave in-flight.json behind, so a bare liveness probe could hit a
    # reused pid; require the process to still be a batch driver.
    try:
        command = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return DRIVER_MARK in command


def live_rows(repo: Path) -> list[str]:
    rows = []
    for state_path in sorted((repo / ".claude/cache/drive-batches").glob("*/*/in-flight.json")):
        try:
            state = json.loads(state_path.read_text())
            pid = int(state["driver_pid"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if _driver_alive(pid):
            rows.append(
                f"{state.get('batch_name', state_path.parent.name)}:{state.get('stage', '?')}"
            )
    return rows


def main() -> int:
    if os.environ.get("GENOMICS_LIVE_BATCH_EDIT_OK") == "1":
        return 0
    try:
        envelope = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(envelope, dict):
        return 0
    tool_input = envelope.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not isinstance(target, str) or not target:
        return 0
    path = Path(target)
    if not path.is_absolute():
        path = Path(envelope.get("cwd") or os.getcwd()) / path
    try:
        relative = Path(os.path.realpath(path)).relative_to(os.path.realpath(REPO))
    except ValueError:
        return 0
    if not relative.parts or relative.parts[0] not in SOURCE_ROOTS:
        return 0
    rows = live_rows(REPO)
    if not rows:
        return 0
    print(
        f"BLOCKED: a genomics drive-batch row is in flight ({', '.join(rows)}). Editing "
        f"main's {relative.parts[0]}/ now makes every native launch refuse "
        "(DirtyGitSourceError) and kills the row. Edit in a worktree instead, or pause: "
        f"touch {REPO}/.claude/cache/drive-batches/PAUSE, wait until the batch's "
        "in-flight.json is gone, edit + commit, then remove PAUSE. "
        "Emergency override: GENOMICS_LIVE_BATCH_EDIT_OK=1.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
