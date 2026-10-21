#!/usr/bin/env python3
"""userprompt-disk-reclaim-suggest.py — when the data volume runs low, show the worktree
reclaim candidates and the exact archive command for each. Advisory only: it runs nothing.

UserPromptSubmit and SessionStart hook. The low-disk guard
(`~/dotfiles/scripts/worktree-reap-cron --disk-guard`, every 5 min) writes
`~/.cache/reclaim/worktree-suggestions.json` from `worktree_gc.py suggest --json` while free
space is under 20 GB; this hook only reads that file, so it stays fast.

Scope and dedupe (2026-10-21): only candidates inside the repo holding the payload `cwd` are
listed; elsewhere the hook emits the one-line DISK LOW summary. Per session (state under
~/.claude/cache/disk-reclaim-hook/), the full list repeats only when the candidate set or the
5 GB free-space band changed; the summary shows at most once per band. Harness-injected
prompts (task notifications, peer relays) are skipped via harness_frame.py.

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


BAND_GB = 5.0
STATE_DIR = Path(
    os.environ.get("RECLAIM_HOOK_STATE_DIR", str(Path.home() / ".claude/cache/disk-reclaim-hook"))
)


def _band(free: float) -> int:
    return int(free // BAND_GB)


def _state_path(session: str) -> Path:
    safe = "".join(c for c in (session or "unknown") if c.isalnum() or c in "-_")[:80]
    return STATE_DIR / f"{safe or 'unknown'}.json"


def _load_state(session: str) -> dict:
    try:
        return json.loads(_state_path(session).read_text())
    except (OSError, ValueError):
        return {}


def _save_state(session: str, state: dict) -> None:
    try:
        path = _state_path(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
    except OSError:
        pass  # fail open: worst case the hook repeats itself


def _repo_root(cwd: str) -> str | None:
    """The main repo holding cwd; a lane worktree maps back to its parent repo."""
    if not cwd:
        return None
    path = Path(cwd).expanduser()
    text = str(path)
    if "/.claude/worktrees/" in text:
        return text.split("/.claude/worktrees/", 1)[0]
    for cand in (path, *path.parents):
        if (cand / ".git").exists():
            return str(cand)
    return None


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


def build(free: float, now: float, cwd: str = "") -> tuple[str, str, list[str]]:
    """(summary, context, candidate signature). An empty signature means summary only."""
    head = f"DISK LOW: {free:.1f} GB free on the data volume (guard threshold {LOW_DISK_GB:.0f} GB)."
    try:
        age = now - SUGGESTIONS.stat().st_mtime
        data = json.loads(SUGGESTIONS.read_text())
    except FileNotFoundError:
        return head, head + (
            f" No reclaim suggestion file at {_short(str(SUGGESTIONS))}; the disk guard "
            f"writes it every 5 min below the threshold. Run `{SUGGEST_CMD}` to list candidates."
        ), []
    except (OSError, ValueError) as exc:
        return head, f"{head} The suggestion file is unreadable ({exc}); run `{SUGGEST_CMD}`.", []
    if age > STALE_SECONDS:
        return head, (
            f"{head} The suggestion file is {age / 3600:.1f} h old, so the disk guard is not "
            f"refreshing it; check ~/.cache/reclaim/disk-guard.log and run `{SUGGEST_CMD}`."
        ), []
    listed = [row for row in data.get("candidates", []) if row.get("candidate", True)]
    # Agents in a repo need that repo's worktrees, not every project's (operator 2026-10-21).
    root = _repo_root(cwd)
    in_repo = [row for row in listed if root and str(row.get("path", "")).startswith(root.rstrip("/") + "/")]
    elsewhere = len(listed) - len(in_repo)
    # The file can be up to 5 min old, and a landing may remove a listed tree in between.
    rows = [row for row in in_repo if Path(str(row.get("path", ""))).exists()]
    removed = len(in_repo) - len(rows)
    if not rows and not removed:
        return head, head, []
    removed_note = (
        f" Left out {removed} listed {'tree' if removed == 1 else 'trees'} already removed from disk."
        if removed
        else ""
    )
    if not rows:
        return head, (
            f"{head} worktree_gc suggest lists no existing worktree candidates in this repo"
            + (f" ({elsewhere} in other repos: `{SUGGEST_CMD}`)" if elsewhere else "")
            + "; for other space see `du -sh ~/Projects/*/.claude ~/Library/Caches`."
            + removed_note
        ), []
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
    sig = sorted(str(row.get("path", "")) for row in rows)
    return summary, f"{summary} Largest {min(TOP_N, len(rows))}:\n{body}\n{note}", sig


def _is_harness_frame(prompt: str) -> bool:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from harness_frame import is_harness_frame

        return is_harness_frame(prompt)
    except Exception:
        return prompt.lstrip().startswith("<task-notification>")


def main() -> None:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    event = payload.get("hook_event_name") or "UserPromptSubmit"
    if event == "UserPromptSubmit" and _is_harness_frame(str(payload.get("prompt") or "")):
        return  # task notifications, peer relays, system frames: not the operator's prompt
    free = _free_gb()
    if free >= LOW_DISK_GB:
        return
    now = time.time()
    session = str(payload.get("session_id") or "")
    summary, context, sig = build(free, now, str(payload.get("cwd") or ""))
    state = _load_state(session)
    band = _band(free)
    if sig:
        # Full list only when the candidate set or the 5 GB band moved since the last one.
        if state.get("sig") == sig and state.get("band") == band:
            return
        state.update(sig=sig, band=band, summary_band=band)
    else:
        if state.get("summary_band") == band:
            return
        state.update(summary_band=band)
    state["at"] = now
    _save_state(session, state)
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
