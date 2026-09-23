#!/usr/bin/env python3
"""pretool-live-batch-edit-guard.py — no edits to genomics MAIN's launch source mid-row.

PreToolUse (Write|Edit|NotebookEdit). Blocks an edit to the genomics main checkout's
scripts/ or config/ while a `just drive-batch` row is in flight (a batch dir's
in-flight.json names a live driver pid) or a single-target `just drive` runs from the
main checkout (a live drive_stage.py process whose cwd is main). Every native launch
seals those two roots from HEAD and refuses a dirty tree (`SOURCE_BUNDLE_ROOTS`,
DirtyGitSourceError in genomics scripts/genome_kernel_source_bundle.py), so a mid-row
edit kills the row.

Why: 2026-09-22, twice in one evening. An in-place M322 fix on main killed
syn7sr clinical_report, and a peer session's model-pin sweep killed family_cascade
after 2.8 h plus the next row (genetic_load) and refused a landing. 2026-09-23: a
publisher fix edited on main killed two parallel single-target `just drive` runs
(next_actions, clinical_report), which the batch-only check could not see.

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

# The LIVE_BATCH_GUARD_* variables exist for hermetic tests only.
REPO = Path(os.environ.get("LIVE_BATCH_GUARD_REPO", "/Users/alien/Projects/genomics"))
DRIVER_MARK = os.environ.get("LIVE_BATCH_GUARD_DRIVER_MARK", "drive_batch.py")
DRIVE_MARK = os.environ.get("LIVE_BATCH_GUARD_DRIVE_MARK", "drive_stage.py")
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


def _process_cwd(pid: int) -> str | None:
    try:
        listing = subprocess.run(
            ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return next((line[1:] for line in listing.splitlines() if line.startswith("n")), None)


def live_drives(repo: Path) -> list[str]:
    """Single-target drives running from the main checkout, as sample:stage labels.

    A drive launched from a worktree seals that worktree's tree, so only a main cwd counts.
    One drive shows up as several processes (just's shell, uv, python); labels dedupe them.
    """
    try:
        listing = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    main_checkout = os.path.realpath(repo)
    labels = set()
    for line in listing.splitlines():
        pid_text, _, command = line.strip().partition(" ")
        if DRIVE_MARK not in command or not pid_text.isdigit():
            continue
        cwd = _process_cwd(int(pid_text))
        if cwd is None or os.path.realpath(cwd) != main_checkout:
            continue
        words = [word for word in command.split(DRIVE_MARK, 1)[1].split() if word[:1] != "-"]
        labels.add(":".join(words[:2]) or f"pid {pid_text}")
    return sorted(labels)


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
    drives = live_drives(REPO)
    if not rows and not drives:
        return 0
    in_flight = [f"batch row {row}" for row in rows] + [f"drive {drive}" for drive in drives]
    print(
        f"BLOCKED: genomics drives are in flight from main ({', '.join(in_flight)}). Editing "
        f"main's {relative.parts[0]}/ now makes every native launch refuse "
        "(DirtyGitSourceError) and kills the drive. Edit in a worktree instead. A single "
        "drive: wait for it to end. A batch: touch "
        f"{REPO}/.claude/cache/drive-batches/PAUSE, wait until the batch's in-flight.json "
        "is gone, edit + commit, then remove PAUSE. "
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
