#!/usr/bin/env python3
# Gov-ID: hook:worktree-location-guard
# goal: stop hand-rolled `git worktree add /tmp/...` — the unmanaged worktrees
#       that grew /private/tmp to 82 GB by 2026-07-25 with no janitor
# verifier: --selftest
# blast_radius: shared (PreToolUse Bash; Claude + Codex via shim)
"""pretool-worktree-location-guard.py — keep worktrees where a janitor can see them.

Claude Code ships a full worktree lifecycle for the trees IT creates under
`<repo>/.claude/worktrees/`: clean exit removes the tree and branch, a dirty exit
prompts, a periodic sweep reaps subagent/background trees past `cleanupPeriodDays`,
and startup clears trees stranded by a crash. `ExitWorktree`'s contract is explicit
that none of it applies to "worktrees you created manually with `git worktree add`".

Codex has no worktree feature at all and no lifecycle; Cursor creates none here. So
a hand-rolled worktree anywhere else is, by construction, garbage nobody collects.

Measured 2026-07-25: 46 such trees, 75.8 GB, average 2.3 GB each — all from ad-hoc
`git worktree add /tmp/<name>` in agent Bash calls. `worktree_gc` is the backstop for
what still escapes (scripts, launchd, other vendors); this gate is the source fix.

Escape hatch: WORKTREE_LOCATION_OK=1 for the genuine cross-volume case.
Anchor: agent-infra research/2026-07-25-worktree-reclaim-candidates.md
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

MANAGED_SEGMENT = os.path.join(".claude", "worktrees")

# `git worktree add` — tolerate `git -C <path>`, `--no-ext-diff`, global -c k=v.
_WORKTREE_ADD = re.compile(r"\bgit\b[^\n;|&]*?\bworktree\s+add\b")

# Flags that CONSUME the next token, so it is never the worktree path.
_VALUE_FLAGS = {"-b", "-B", "--reason", "--orphan"}


def _extract_path(cmd: str) -> str | None:
    """Return the target path of a `git worktree add`, or None if unparseable."""
    try:
        toks = shlex.split(cmd, comments=False)
    except ValueError:
        return None
    try:
        i = toks.index("worktree")
    except ValueError:
        return None
    if i + 1 >= len(toks) or toks[i + 1] != "add":
        return None

    rest = toks[i + 2 :]
    j = 0
    while j < len(rest):
        t = rest[j]
        if t == "--":
            j += 1
            continue
        if t in _VALUE_FLAGS:
            j += 2
            continue
        if t.startswith("-") and "=" in t:
            j += 1
            continue
        if t.startswith("-"):
            j += 1
            continue
        return t
    return None


def _is_managed(path: str, cwd: str = "") -> bool:
    """True when the path lands inside some repo's .claude/worktrees/."""
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    p = os.path.normpath(p)
    return MANAGED_SEGMENT in p


def verdict(cmd: str, cwd: str = "") -> tuple[str, str]:
    """Return ('block'|'pass', message)."""
    if not cmd or not cmd.strip():
        return "pass", ""
    if os.environ.get("WORKTREE_LOCATION_OK") == "1":
        return "pass", ""
    if not _WORKTREE_ADD.search(cmd):
        return "pass", ""

    path = _extract_path(cmd)
    if path is None:
        # Unparseable shape — fail open rather than block a legitimate call.
        return "pass", ""
    if _is_managed(path, cwd):
        return "pass", ""

    return (
        "block",
        f"BLOCK: `git worktree add {path}` creates a worktree nothing will ever "
        "reclaim.\n"
        "Claude Code's exit-removal, dirty-exit prompt, periodic sweep and "
        "crash-recovery ALL apply only to worktrees under `<repo>/.claude/worktrees/` "
        "(ExitWorktree: \"will NOT touch worktrees you created manually\"). Codex has "
        "no worktree lifecycle at all.\n"
        "Use instead:\n"
        "  • EnterWorktree (this session)  or  `claude --worktree <name>` (new session)\n"
        f"  • or target the managed dir: git worktree add <repo>/{MANAGED_SEGMENT}/<name>\n"
        "Genuine cross-volume need: WORKTREE_LOCATION_OK=1.\n"
        "Why: 46 hand-rolled trees = 75.8 GB with no janitor (2026-07-25).",
    )


def _selftest() -> int:
    home = os.path.expanduser("~")
    gx = f"{home}/Projects/genomics"
    cases: list[tuple[str, str, str]] = [
        # (cmd, cwd, want)
        ("git worktree add /tmp/lane-a", gx, "block"),
        ("git worktree add /private/tmp/kernel-lane-veccut", gx, "block"),
        ("git worktree add --detach /tmp/x HEAD", gx, "block"),
        ("git worktree add -b rescue/foo /tmp/rescue-land", gx, "block"),
        ("git -C ~/Projects/genomics worktree add /tmp/y", gx, "block"),
        ("git --no-ext-diff worktree add ../sibling-tree", gx, "block"),
        ("git worktree add lane-b", gx, "block"),  # relative, outside managed
        # allowed
        (f"git worktree add {gx}/.claude/worktrees/lane-a", gx, "pass"),
        (f"git worktree add -b k/x {gx}/.claude/worktrees/kx", gx, "pass"),
        (".claude/worktrees/rel && git worktree add .claude/worktrees/rel", gx, "pass"),
        # non-add worktree verbs must never fire
        ("git worktree list", gx, "pass"),
        ("git worktree remove /tmp/lane-a", gx, "pass"),
        ("git worktree prune", gx, "pass"),
        # unrelated
        ("git commit -m 'worktree add note'", gx, "pass"),
        ("echo git worktree add /tmp/doc >> README.md", gx, "block"),
    ]
    bad = 0
    for cmd, cwd, want in cases:
        got, _ = verdict(cmd, cwd)
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} want={want:<5} got={got:<5} {cmd}")

    os.environ["WORKTREE_LOCATION_OK"] = "1"
    got, _ = verdict("git worktree add /tmp/escape", gx)
    ok = got == "pass"
    bad += not ok
    print(f"  {'ok  ' if ok else 'FAIL'} want=pass  got={got:<5} (WORKTREE_LOCATION_OK=1)")
    del os.environ["WORKTREE_LOCATION_OK"]

    total = len(cases) + 1
    print("PASS" if not bad else "FAIL", f"{total - bad}/{total}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash", "Shell"):
        return 0
    ti = payload.get("tool_input") or {}
    action, msg = verdict(ti.get("command", ""), payload.get("cwd") or "")
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
