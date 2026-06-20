#!/usr/bin/env python3
"""stop-mass-deletion-guard.py — Stop hook: WARN when many tracked files have vanished
from the working tree as UNSTAGED deletions (` D` in `git status --porcelain`) — the
peer-clobber / accidental-`rm` signal.

WHY THIS EXISTS (caught live 2026-06-20): a concurrent **Cursor** peer agent sharing the
checkout `rm -rf`'d the entire `docs/` tree — every ADR, including freshly-authored ones.
It was found only by a manual `git status` before a commit; a `git commit -a` / `git add -A`
would have committed the loss. The existing "concurrent peer -> worktree" rule + SessionStart
warning miss this because the clobberer is NOT a `claude` peer (different tool, no shared-state
detection), and `stop-uncommitted-warn.sh` guards additions, not deletions.

The signal is precise: the Edit/Write tools never delete, and intentional removals go through
`git rm` (which STAGES the deletion -> `D ` in porcelain). So a BURST of UNSTAGED worktree
deletions (` D`) means files disappeared from disk by something else — a peer agent, a runaway
script, or an accident — and they are still in HEAD (recoverable).

WARN-only (never blocks -> no iatrogenic harm). Fail-open on any error (never breaks the stop).
"""
import json
import os
import subprocess
import sys

THRESHOLD = 5  # unstaged tracked-file deletions that trip the warning


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("stop_hook_active"):
        return  # re-entrancy guard
    cwd = data.get("cwd") or ""
    if not cwd or not os.path.isdir(os.path.join(cwd, ".git")):
        return
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--no-renames"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        ).stdout
    except Exception:
        return

    # porcelain "XY path": X=index/staged, Y=worktree. " D" = tracked file deleted from the
    # worktree but NOT staged (no `git rm`). "D " (staged) is an intentional removal — ignored.
    deleted = [ln[3:] for ln in out.splitlines() if len(ln) >= 3 and ln[0] == " " and ln[1] == "D"]
    if len(deleted) < THRESHOLD:
        return

    n = len(deleted)
    shown = "\n".join("  " + p for p in deleted[:15])
    more = f"\n  ... and {n - 15} more" if n > 15 else ""
    msg = (
        f"MASS DELETION GUARD: {n} tracked files vanished from the working tree as UNSTAGED "
        f"deletions (no `git rm`). The Edit/Write tools never delete and intentional removals are "
        f"staged, so this is most likely a concurrent peer agent (cursor/codex), a runaway script, "
        f"or an accident -- NOT your work. They are still in HEAD (recoverable). VERIFY before "
        f"committing (`git commit -a` / `git add -A` would commit the loss):\n{shown}{more}\n"
        f"Recover:  git -C {cwd} checkout HEAD -- <paths>  (or the whole tree). "
        f"If the deletion IS intentional, `git rm` them so it is a deliberate staged change."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-open: never break the stop
    sys.exit(0)
