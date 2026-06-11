#!/usr/bin/env python3
"""PreToolUse:Agent — block a worktree-isolated dispatch that will be stale-blind.

What a worktree subagent sees depends on the ``worktree.baseRef`` setting
(introduced in Claude Code v2.1.133):

- ``"fresh"`` (harness default): worktree branches from origin/HEAD. The
  subagent is blind to ALL unpushed local commits AND uncommitted changes.
- ``"head"`` (our global setting since 2026-06-12): worktree branches from
  local HEAD. Unpushed commits are visible; only UNCOMMITTED changes are
  invisible.

If the dispatch *task* references files the worktree won't have current, the
subagent silently STOP-and-no-ops (~150K tokens wasted) — the failure that ate
a dispatch on 2026-05-29 (genomics). Probe-verified 2026-06-11 and 2026-06-12
in agent-infra: fresh mode → worktree got origin/main exactly (36 commits
stale); head mode → worktree got local HEAD, dirty files still invisible.

This guard resolves the effective baseRef (project settings.local.json →
project settings.json → ~/.claude/settings.json → "fresh") and checks exactly
the blind spot of the active mode:

- head mode: prompt references an uncommitted (dirty/untracked) path → block.
- fresh mode: prompt references a path changed in origin/main..HEAD OR a
  dirty path → block.

Surgical, not blunt: safe dispatches pass silently. Fail-open on any error.
Override: WORKTREE_STALE_OK=1 (use only if the referenced files are current
at the worktree's branch point).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

# Ubiquitous basenames — too common to use for a basename match (path match still applies).
_COMMON = {"__init__.py", "conftest.py", "README.md", "setup.py", "__main__.py", "index.md", "main.py"}


def _sh(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def _base_ref_setting(cwd: str) -> str:
    """Resolve worktree.baseRef the way the harness does: project local > project > user."""
    candidates = [
        os.path.join(cwd, ".claude", "settings.local.json"),
        os.path.join(cwd, ".claude", "settings.json"),
        os.path.expanduser("~/.claude/settings.json"),
    ]
    for path in candidates:
        try:
            with open(path) as fh:
                value = json.load(fh).get("worktree", {}).get("baseRef")
            if value in ("head", "fresh"):
                return value
        except Exception:
            continue
    return "fresh"  # harness default since v2.1.133


def _dirty_paths() -> list[str]:
    """Uncommitted paths (staged, unstaged, untracked) — invisible in BOTH modes."""
    paths: list[str] = []
    for line in _sh(["git", "status", "--porcelain"]).splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:  # rename: guard the new name
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip('"'))
    return paths


def _match(paths: list[str], prompt: str, why: str) -> list[str]:
    hits: list[str] = []
    for path in paths:
        base = os.path.basename(path)
        if path in prompt:
            hits.append(f"{path} ({why})")
        elif base not in _COMMON and len(base) >= 8 and base in prompt:
            hits.append(f"{path} (basename '{base}'; {why})")
    return hits


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # malformed payload -> fail open

    if data.get("tool_name") != "Agent":
        return 0
    tool_input = data.get("tool_input") or {}
    if tool_input.get("isolation") != "worktree":
        return 0
    prompt = tool_input.get("prompt") or ""
    if not prompt:
        return 0

    mode = _base_ref_setting(data.get("cwd") or os.getcwd())

    hits = _match(_dirty_paths(), prompt, "UNCOMMITTED — invisible in any worktree")
    ahead = "0"
    if mode == "fresh":
        # origin/main is the worktree's branch point. No origin/main -> nothing more to guard.
        if subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "origin/main"],
            capture_output=True,
        ).returncode == 0:
            ahead = _sh(["git", "rev-list", "--count", "origin/main..HEAD"]) or "0"
            if ahead != "0":
                changed = [l for l in _sh(["git", "diff", "--name-only", "origin/main..HEAD"]).splitlines() if l]
                hits += _match(changed, prompt, "changed in origin/main..HEAD; worktree branches from origin/main")

    if not hits:
        return 0

    if os.environ.get("WORKTREE_STALE_OK") == "1":
        print(
            "[worktree-staleness-guard] WARN: dispatch references files the worktree won't have; "
            "WORKTREE_STALE_OK=1 set, allowing.",
            file=sys.stderr,
        )
        return 0

    base_desc = (
        "local HEAD (worktree.baseRef=head); uncommitted changes are NOT included"
        if mode == "head"
        else f"origin/main ({ahead} commits behind local main); unpushed commits and uncommitted changes are NOT included"
    )
    fixes = ["  1. commit the dirty files first (worktree then includes them)"]
    if mode == "fresh":
        fixes.append("  2. git push origin main, or set worktree.baseRef=head in settings")
    fixes += [
        f'  {len(fixes) + 1}. dispatch WITHOUT isolation:"worktree" (subagent sees the local working tree)',
        f"  {len(fixes) + 2}. WORKTREE_STALE_OK=1 to override (only if the referenced files are current at the branch point)",
    ]
    lines = [
        f"[worktree-staleness-guard] BLOCKED: worktree subagent branches from {base_desc}.",
        "The dispatch prompt references files the worktree will NOT have current —",
        "the subagent will silently no-op (~150K tokens):",
        *[f"  - {h}" for h in hits[:8]],
        "Fix one of:",
        *fixes,
    ]
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # never block on an internal error
