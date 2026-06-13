#!/usr/bin/env python3
"""Tests for pretool-inventory-dispatch.py.

Runs the hook as a subprocess with crafted envelopes and asserts the advisory
fires only on research/exploration dispatches whose topic overlaps recent commits
in the cwd. Uses a throwaway git repo for deterministic commit-overlap cases so
the test does not depend on the agent-infra log.

Run: python3 test_inventory_dispatch.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-inventory-dispatch.py"


def run(envelope: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(envelope), capture_output=True, text=True, timeout=10,
    )
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}: {p.stderr}"
    return p.stdout.strip()


def fires(out: str) -> bool:
    if not out:
        return False
    obj = json.loads(out)
    return "INVENTORY-BEFORE-DISPATCH" in obj["hookSpecificOutput"]["additionalContext"]


def make_repo(tmp: Path, subjects: list[str], name: str = "repo") -> Path:
    repo = tmp / name
    repo.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    g("init", "-q")
    g("config", "user.email", "t@t.t")
    g("config", "user.name", "t")
    for i, subj in enumerate(subjects):
        (repo / f"f{i}").write_text(str(i))
        g("add", f"f{i}")
        g("commit", "-q", "-m", subj)
    return repo


def main() -> int:
    failures = []

    def check(name: str, cond: bool):
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        repo = make_repo(tmp, [
            "[corpus] Wire transactional outbox for verdict attestation",
            "[research] Map peroxisome biogenesis pathways",
            "Unrelated chore: bump deps",
        ])
        cwd = str(repo)

        # Positive: research dispatch overlapping a distinctive commit topic.
        check("positive: overlapping research dispatch fires", fires(run({
            "tool_name": "Agent", "cwd": cwd,
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate the verdict attestation outbox design",
                           "prompt": "research how attestation works"},
        })))

        # Negative: research dispatch with no commit overlap.
        check("negative: non-overlapping topic is silent", not fires(run({
            "tool_name": "Agent", "cwd": cwd,
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate mitochondrial dynamics",
                           "prompt": "research fission fusion"},
        })))

        # Negative: no research intent (implementation rename).
        check("negative: no research intent is silent", not fires(run({
            "tool_name": "Agent", "cwd": cwd,
            "tool_input": {"subagent_type": "claude",
                           "description": "Rename attestation variable to verdict",
                           "prompt": "edit and rename the symbol"},
        })))

        # Negative: worktree isolation (implementation continuation) skipped.
        check("negative: worktree dispatch is silent", not fires(run({
            "tool_name": "Agent", "cwd": cwd, "isolation": "worktree",
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate attestation outbox",
                           "prompt": "research attestation"},
        })))

        # Positive: a CURATED memo (research/ filename) matches even with NO git
        # overlap — the months-old-memo rediscovery case the git scan is blind to.
        memo_repo = make_repo(tmp, ["Unrelated chore: bump deps"], "memo_repo")
        (memo_repo / "research").mkdir()
        (memo_repo / "research" / "2026-06-12-symphony-orchestrator-reference.md").write_text("x")
        check("positive: curated memo filename fires without git overlap", fires(run({
            "tool_name": "Agent", "cwd": str(memo_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Research symphony orchestrator patterns",
                           "prompt": "prior art on symphony orchestration"},
        })))

        # Negative: research dispatch ABOUT worktrees must NOT be skipped as an
        # isolation dispatch (the 2026-06-13 false-negative). With a matching memo
        # it should fire despite the word 'worktree' in the prompt.
        wt_repo = make_repo(tmp, ["Unrelated chore: bump deps"], "wt_repo")
        (wt_repo / "research").mkdir()
        (wt_repo / "research" / "worktree-orchestrators-survey.md").write_text("x")
        check("positive: research ABOUT worktrees not skipped", fires(run({
            "tool_name": "Agent", "cwd": str(wt_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Survey worktree orchestrators prior art",
                           "prompt": "research worktree orchestrator tools"},
        })))

        # Negative: an ACTUAL isolation dispatch (structured field) stays skipped.
        check("negative: isolation=worktree field still skipped", not fires(run({
            "tool_name": "Agent", "cwd": str(wt_repo), "isolation": "worktree",
            "tool_input": {"subagent_type": "researcher",
                           "description": "Survey worktree orchestrators prior art",
                           "prompt": "research worktree orchestrator tools"},
        })))

        # Fail-open: garbage stdin still exits 0 with no output.
        p = subprocess.run([sys.executable, str(HOOK)], input="not json{",
                           capture_output=True, text=True, timeout=10)
        check("fail-open: garbage input exits 0, no output",
              p.returncode == 0 and not p.stdout.strip())

    print()
    if failures:
        print(f"{len(failures)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
