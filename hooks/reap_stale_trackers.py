#!/usr/bin/env python3
"""Reap stale per-session/per-PPID tracker files from the hook state dir.

WHY THIS EXISTS
---------------
Hooks across every repo write one tracker per (session, PPID) into ``/tmp``:
``claude-bash-snapshot-*``, ``claude-write-intent-*``, ``claude-head-snapshot-*``,
``claude-toolcount-*``, ``claude-cost-check-*``, ``claude-tab-error-*``,
``claude-non-agent-*``, ``claude-session-touched-*``. Nothing ever reaped them, and
subagents multiply them (each gets its own PPID).

Measured 2026-07-13: **312,368** such files had accumulated. genomics'
``staged_ownership_guard.py`` runs ``glob.glob()`` over that directory FOUR times per
commit, so every commit paid ~5.6s scanning 312k dirents. After reaping 307k files the
same glob went 1.407s -> 0.008s. The leak is the cost; this module stops it recurring.

SAFETY CONTRACT (do not weaken)
-------------------------------
A tracker grants a session ownership of files it edited. Deleting a *live* session's
tracker would make its own files look "foreign" to the commit guard and block it. So:

1. Never delete a file whose owning PID is still alive.
2. Never delete anything younger than ``MIN_AGE_S`` (60 min). The consuming guard only
   trusts trackers inside a 30-minute window (``RECENT_PPID_GRACE_SECONDS``), so a 60-min
   floor is 2x that: nothing we delete could have changed an ownership decision.
3. Unknown/undecidable PID state => treat as ALIVE and keep. Fail safe, never destructive.

Throttled: at most one scan per ``THROTTLE_S`` (stamp file), so the per-tool-call cost is
a single ``stat()``. Fail-open: any error is swallowed; a reaper must never break a tool call.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

THROTTLE_S = 600  # scan at most once every 10 minutes
MIN_AGE_S = 3600  # never touch anything younger than 60 min (2x the guard's 30-min window)
STAMP_NAME = ".claude-tracker-reap-stamp"
PID_SUFFIX = re.compile(r"-(\d+)(?:\.txt)?$")


def _pid_alive(pid: int) -> bool:
    """True if ``pid`` exists. Conservative: anything undecidable counts as alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by another user
    except OSError:
        return True  # undecidable -> never delete
    return True


def _throttled(state_dir: str, now: float) -> bool:
    """True if a reap ran within THROTTLE_S. Claims the stamp when it returns False."""
    stamp = os.path.join(state_dir, STAMP_NAME)
    try:
        if now - os.path.getmtime(stamp) < THROTTLE_S:
            return True
    except OSError:
        pass  # no stamp yet -> first run
    # Claim the window BEFORE scanning so concurrent hooks don't all scan.
    try:
        with open(stamp, "w") as handle:
            handle.write(str(int(now)))
    except OSError:
        return True  # can't claim -> don't scan
    return False


def reap(state_dir: str = "/tmp", *, min_age_s: int = MIN_AGE_S, dry_run: bool = False) -> int:
    """Unlink dead-PID trackers older than ``min_age_s``. Returns the count."""
    now = time.time()
    removed = 0
    try:
        entries = os.scandir(state_dir)
    except OSError:
        return 0
    with entries:
        for entry in entries:
            name = entry.name
            if not name.startswith("claude-"):
                continue
            try:
                if not entry.is_file(follow_symlinks=False):
                    continue
                if now - entry.stat(follow_symlinks=False).st_mtime < min_age_s:
                    continue  # rule 2: too young to touch
            except OSError:
                continue
            match = PID_SUFFIX.search(name)
            if match is None:
                continue  # no owner we can prove -> keep
            if _pid_alive(int(match.group(1))):
                continue  # rule 1: live session keeps its claims
            if dry_run:
                removed += 1
                continue
            try:
                os.unlink(entry.path)
                removed += 1
            except OSError:
                pass
    return removed


def maybe_reap(state_dir: str = "/tmp") -> int:
    """Throttled reap for hook call sites. Never raises."""
    try:
        if _throttled(state_dir, time.time()):
            return 0
        return reap(state_dir)
    except Exception:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=os.environ.get("CLAUDE_HOOK_STATE_DIR", "/tmp"))
    parser.add_argument("--apply", action="store_true", help="actually unlink (default: dry-run)")
    parser.add_argument("--force", action="store_true", help="ignore the throttle stamp")
    args = parser.parse_args(argv)

    if not args.force and not args.apply:
        count = reap(args.state_dir, dry_run=True)
        print(f"reap-stale-trackers: {count} dead-PID tracker(s) older than {MIN_AGE_S}s (dry-run)")
        return 0
    count = reap(args.state_dir, dry_run=not args.apply)
    verb = "unlinked" if args.apply else "would unlink"
    print(f"reap-stale-trackers: {verb} {count} dead-PID tracker(s) in {args.state_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
