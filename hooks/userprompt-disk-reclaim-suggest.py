#!/usr/bin/env python3
"""userprompt-disk-reclaim-suggest.py — when the data volume runs low, show the worktree
reclaim candidates and the exact archive command for each. Advisory only: it runs nothing.

UserPromptSubmit and SessionStart hook. The low-disk guard
(`~/dotfiles/scripts/worktree-reap-cron --disk-guard`, every 5 min) writes
`~/.cache/reclaim/worktree-suggestions.json` from `worktree_gc.py suggest --json` while free
space is under 20 GB; this hook only reads that file, so it stays fast.

Gov-ID: hook:disk-reclaim-suggest | verifier: test_userprompt_disk_reclaim_suggest.py
goal: operator ruling 2026-10-12 — no automatic cleanup may archive or delete a worktree that
still holds unlanded work, in any project; automation only suggests. On 2026-10-12 the disk
reached 0 bytes, macOS suspended Ghostty for swap exhaustion, and the space sat in lane
worktrees no automatic pass was allowed to remove.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

LOW_DISK_GB = float(os.environ.get("RECLAIM_LOW_DISK_GB", "20"))
CRITICAL_GB = 5.0
REPEAT_SECONDS = 30 * 60
CRITICAL_REPEAT_SECONDS = 10 * 60
STALE_SECONDS = 60 * 60
TOP_N = 5
CACHE = Path(os.environ.get("RECLAIM_CACHE_DIR", str(Path.home() / ".cache/reclaim")))
SUGGESTIONS = CACHE / "worktree-suggestions.json"
SUGGEST_CMD = (
    "uv run --project ~/Projects/agent-infra --no-sync python3 "
    "~/Projects/agent-infra/scripts/worktree_gc.py suggest --all-projects "
    "--lock-max-age-hours 72"
)


def _free_gb() -> float:
    override = os.environ.get("RECLAIM_FREE_GB_OVERRIDE")
    if override is not None:
        return float(override)
    return shutil.disk_usage(Path.home()).free / 1e9


def _due(session: str, free: float, now: float) -> bool:
    """Rate limit per session: once per 30 min, every 10 min below 5 GB."""
    state = CACHE / "suggest-hook-state" / f"{session or 'unknown'}.json"
    try:
        last = json.loads(state.read_text())
    except (OSError, ValueError):
        last = {}
    wait = CRITICAL_REPEAT_SECONDS if free < CRITICAL_GB else REPEAT_SECONDS
    if now - float(last.get("at", 0)) < wait and free >= float(last.get("free_gb", 0)) - 5:
        return False
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"at": now, "free_gb": free}))
    return True


def _short(path: str) -> str:
    home = str(Path.home())
    return "~" + path[len(home) :] if path.startswith(home) else path


def _line(row: dict) -> str:
    size = row.get("size_bytes") or 0
    unlanded = row.get("unmatched_commits")
    parts = [
        f"{size / 1e9:.1f} GB",
        str(row.get("class", "?")),
        _short(str(row.get("path", "?"))),
        f"idle {float(row.get('idle_hours') or 0):.0f} h",
        f"{row.get('dirty_count', '?')} dirty",
        f"{row.get('commits_not_on_default', '?')} commits off main"
        + (f" ({unlanded} with no landed match)" if unlanded else ""),
    ]
    if row.get("lock_reason"):
        parts.append(f"locked: {str(row['lock_reason'])[:80]}")
    return "- " + ", ".join(parts) + f"\n  archive: `{row.get('archive_command', '?')}`"


def build(free: float, now: float) -> tuple[str, str]:
    head = f"DISK LOW: {free:.1f} GB free on the data volume (guard threshold {LOW_DISK_GB:.0f} GB)."
    try:
        age = now - SUGGESTIONS.stat().st_mtime
        data = json.loads(SUGGESTIONS.read_text())
    except FileNotFoundError:
        return head, (
            f"{head} No reclaim suggestion file at {_short(str(SUGGESTIONS))}; the disk guard "
            f"writes it every 5 min below the threshold. Run `{SUGGEST_CMD}` to list candidates."
        )
    except (OSError, ValueError) as exc:
        return head, f"{head} The suggestion file is unreadable ({exc}); run `{SUGGEST_CMD}`."
    if age > STALE_SECONDS:
        return head, (
            f"{head} The suggestion file is {age / 3600:.1f} h old, so the disk guard is not "
            f"refreshing it; check ~/.cache/reclaim/disk-guard.log and run `{SUGGEST_CMD}`."
        )
    listed = [row for row in data.get("candidates", []) if row.get("candidate", True)]
    # The file can be up to 5 min old, and a landing may remove a listed tree in between.
    rows = [row for row in listed if Path(str(row.get("path", ""))).exists()]
    removed = len(listed) - len(rows)
    removed_note = (
        f" Left out {removed} listed {'tree' if removed == 1 else 'trees'} already removed from disk."
        if removed
        else ""
    )
    if not rows:
        return head, (
            f"{head} worktree_gc suggest lists no existing worktree candidates "
            f"({len(data.get('not_candidates', []))} trees excluded as live or protected); "
            "the space is elsewhere (`du -sh ~/Projects/*/.claude ~/Library/Caches`)."
            + removed_note
        )
    rows.sort(key=lambda row: row.get("size_bytes") or 0, reverse=True)
    total = sum(row.get("size_bytes") or 0 for row in rows) / 1e9
    unlanded = sum(1 for row in rows if row.get("unmatched_commits") or row.get("dirty_count"))
    body = "\n".join(_line(row) for row in rows[:TOP_N])
    note = (
        "Nothing is removed automatically. Before archiving a tree, check whether its commits "
        "or dirty edits have landed; `archive` pins HEAD under refs/wt-archive/ and saves the "
        "diff, untracked files and .claude/cache results first. Ask the operator before "
        "archiving work that has not landed."
    )
    summary = (
        f"{head} {len(rows)} worktree reclaim candidates hold {total:.1f} GB; "
        f"{unlanded} carry dirty edits or unlanded commits.{removed_note}"
    )
    return summary, f"{summary} Largest {min(TOP_N, len(rows))}:\n{body}\n{note}"


def main() -> None:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    event = payload.get("hook_event_name") or "UserPromptSubmit"
    free = _free_gb()
    if free >= LOW_DISK_GB:
        return
    now = time.time()
    if not _due(str(payload.get("session_id") or ""), free, now):
        return
    summary, context = build(free, now)
    print(
        json.dumps(
            {
                "systemMessage": summary,
                "hookSpecificOutput": {"hookEventName": event, "additionalContext": context},
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # advisory hook: report, never block the prompt
        print(f"userprompt-disk-reclaim-suggest: {exc}", file=sys.stderr)
    sys.exit(0)
