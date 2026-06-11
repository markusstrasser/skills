#!/usr/bin/env python3
"""PreToolUse:Agent — block a worktree-isolated dispatch that will be stale-blind.

Worktree subagents branch from ``origin/main``, NOT local HEAD. Mid-session local
main is routinely far ahead of origin (commits aren't pushed often), so a worktree
sees a stale base missing this session's work. If the dispatch *task* references
files that exist only in those unpushed commits, the subagent silently STOP-and-
no-ops (~150K tokens wasted) — the failure that ate a dispatch on 2026-05-29
(genomics). Re-confirmed empirically 2026-06-11 in agent-infra: local main 24
commits ahead of origin → worktree probe agent got origin/main exactly, blind to
all local commits and uncommitted changes.

Lifted from genomics ``.claude/hooks/`` to shared hooks 2026-06-11 and wired
globally (~/.claude/settings.json, PreToolUse:Agent) — every repo with worktree
dispatches has this failure mode. Genomics' SessionStart hooks WARN the subagent
*after* its stale worktree exists; that's too late (it can't do a task whose
files aren't there). This guards the *parent* at dispatch time, *before* the
worktree is created.

Surgical, not blunt: it does NOT block every dispatch when local is ahead (that
would fire constantly and train blind overrides). It blocks ONLY when the prompt
references a path that ``git diff origin/main..HEAD`` shows changed locally — i.e.
exactly the files the worktree won't have current. Safe dispatches pass silently.

Fail-open: any error or missing origin/main exits 0 (never block spuriously).
Override: WORKTREE_STALE_OK=1 (use only if the referenced files exist in origin/main).
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

    # origin/main is the worktree's branch point. No origin/main -> nothing to guard.
    if subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "origin/main"],
        capture_output=True,
    ).returncode != 0:
        return 0

    ahead = _sh(["git", "rev-list", "--count", "origin/main..HEAD"]) or "0"
    if ahead == "0":
        return 0  # worktree base == local HEAD; fresh.

    changed = [line for line in _sh(["git", "diff", "--name-only", "origin/main..HEAD"]).splitlines() if line]
    if not changed:
        return 0

    prompt = tool_input.get("prompt") or ""
    if not prompt:
        return 0

    hits: list[str] = []
    for path in changed:
        base = os.path.basename(path)
        if path in prompt:
            hits.append(f"{path} (path referenced; changed in origin/main..HEAD)")
        elif base not in _COMMON and len(base) >= 8 and base in prompt:
            hits.append(f"{path} (basename '{base}' referenced; changed locally)")

    if not hits:
        return 0  # prompt references only origin-current files -> worktree is fine.

    if os.environ.get("WORKTREE_STALE_OK") == "1":
        print(
            "[worktree-staleness-guard] WARN: dispatch references locally-changed files; "
            "WORKTREE_STALE_OK=1 set, allowing.",
            file=sys.stderr,
        )
        return 0

    lines = [
        f"[worktree-staleness-guard] BLOCKED: worktree subagent branches from origin/main "
        f"({ahead} commits behind local main).",
        "The dispatch prompt references files changed locally since origin/main — the worktree",
        "will NOT have them and the subagent will silently no-op (~150K tokens):",
        *[f"  - {h}" for h in hits[:8]],
        "Fix one of:",
        "  1. git push origin main   (then retry — worktree then branches from current main)",
        '  2. dispatch WITHOUT isolation:"worktree" (subagent sees the local working tree)',
        "  3. do the task inline if it tightly depends on freshly-written local files",
        "  4. WORKTREE_STALE_OK=1 to override (only if those files already exist in origin/main)",
    ]
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # never block on an internal error
