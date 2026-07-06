#!/usr/bin/env python3
"""peer-work-visibility.py — per-peer WORK detail for the SessionStart peer warning.

Turns "N peers share this checkout" into "what are they touching", so an agent can pick a
different front or coordinate BEFORE starting work. Consumed by sessionstart-peer-session-warn.sh
when peer-session-count.sh reports >=1 live peer.

Two live, session-attributed signals (no agentlogs join — git is live and hot-path-safe):
  (a) UNCOMMITTED dirty tracked paths in the working tree. At SessionStart these are by
      construction NOT this just-started session's edits -> they are peer / prior-session work.
  (b) Recent commit subjects (last N hours) whose Session-ID trailer != mine -> peer topics.

Usage:  peer-work-visibility.py <cwd> [<my_session_id>]
Prints bounded advisory lines to stdout (indented, ready to echo). Nothing + exit 0 on any error
or when there is no peer work to show (the iatrogenic guard: no noise when peers are idle).
"""
from __future__ import annotations

import subprocess
import sys

HOURS = 6
MAX_PATHS = 6
MAX_COMMITS = 4


def _git(cwd: str, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", cwd, "--no-pager", *args],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def dirty_paths(cwd: str) -> list[str]:
    """Tracked files modified/added in the working tree (peer/prior-session dirt at SessionStart)."""
    out = _git(cwd, "status", "--porcelain", "--no-renames", "--untracked-files=no")
    paths = []
    for ln in out.splitlines():
        if len(ln) < 4:
            continue
        # XY path; take anything with a modification/add in index or worktree
        if ln[0] in "MA" or ln[1] in "MA":
            paths.append(ln[3:].strip())
    return paths


def peer_commits(cwd: str, my_sid: str) -> list[str]:
    """Recent commit subjects whose Session-ID trailer differs from mine."""
    out = _git(
        cwd, "log", f"--since={HOURS} hours ago", "--no-merges",
        "--format=%h\x1f%s\x1f%(trailers:key=Session-ID,valueonly)",
    )
    rows = []
    for ln in out.splitlines():
        parts = ln.split("\x1f")
        if len(parts) < 3:
            continue
        h, subj, sid = parts[0], parts[1], parts[2].strip()
        if my_sid and sid == my_sid:
            continue  # mine — skip
        rows.append(f"{subj}  ({sid[:8] or h})")
    return rows


def main() -> None:
    if len(sys.argv) < 2:
        return
    cwd = sys.argv[1]
    my_sid = sys.argv[2] if len(sys.argv) > 2 else ""

    paths = dirty_paths(cwd)
    commits = peer_commits(cwd, my_sid)
    if not paths and not commits:
        return  # nothing to show -> no noise (iatrogenic guard)

    lines = ["   ── peer work in this checkout (coordinate before touching these) ──"]
    if paths:
        shown = paths[:MAX_PATHS]
        more = f"  (+{len(paths) - MAX_PATHS} more)" if len(paths) > MAX_PATHS else ""
        lines.append(f"     uncommitted paths: {', '.join(shown)}{more}")
    if commits:
        lines.append("     recent peer commits:")
        for c in commits[:MAX_COMMITS]:
            lines.append(f"       - {c}")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-open: never break SessionStart
    sys.exit(0)
