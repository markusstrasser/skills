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
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-inventory-dispatch.py"


def run(envelope: dict) -> str:
    # The hook logs every fire for ROI measurement; these fixtures ("attestation, outbox,
    # verdict", "orchestrator, symphony") had been landing in the real log as skills-repo fires.
    env = dict(os.environ, HOOK_TRIGGER_LOG=os.devnull)
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(envelope), capture_output=True, text=True, timeout=10, env=env,
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

        # --- 2026-09-21 retune: 87 of 152 fires were keyed on directory names from paths.
        # A repo whose memos all share its name as a prefix, like immigration-research.
        topic_repo = make_repo(tmp, ["[analysis] Match fiscal benefits — preserve private tax offsets"],
                               "immigration-research")
        (topic_repo / "research").mkdir()
        for stem in ("fiscal-impact", "crime-rates", "nlsy97-parent-linkage", "cultural-output",
                     "detention-costs", "school-peers", "housing-rents", "wage-effects",
                     "remittances", "naturalization", "enforcement-history", "visa-overstays"):
            (topic_repo / "research" / f"immigration-{stem}.md").write_text("x")
        brief = f"{topic_repo}/infra/immigration-fiscal/lane/BRIEF.md"

        check("negative: directory names inside a path are not topic keywords", not fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Read the Misery of Diversity paper",
                           "prompt": f"First read {brief} and follow it exactly. "
                                     "Notes go to /private/tmp/claude-501/scratch/notes.md"},
        })))
        check("negative: a path containing 'research' is not research intent", not fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "general-purpose",
                           "description": "Guard test",
                           "prompt": f"Make one Write call to {topic_repo}/scratch/private/x.json"},
        })))
        check("negative: reporting scaffolding words are not topic keywords", not fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "Explore",
                           "description": "Probe hook envelope",
                           "prompt": "Make exactly one call. The parent reads a log, not your output."},
        })))
        check("negative: the repo's shared memo prefix selects nothing", not fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate immigration court backlogs",
                           "prompt": "research immigration judges and asylum grant rates"},
        })))
        check("positive: a distinctive memo keyword still fires in that repo", fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate remittances to Mexico",
                           "prompt": "research remittances outflows by origin"},
        })))
        # A brief under "<name>-research/infra/" is not a cited memo: the repo's name must not
        # satisfy the "prompt already cites research/*.md" exemption.
        check("positive: a repo named *-research does not silence the check", fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate remittances to Mexico",
                           "prompt": f"First read {brief}. Then research remittances outflows."},
        })))
        check("negative: a memo cited by path still means the inventory was done", not fires(run({
            "tool_name": "Agent", "cwd": str(topic_repo),
            "tool_input": {"subagent_type": "researcher",
                           "description": "Investigate remittances to Mexico",
                           "prompt": "Extend research/immigration-remittances.md with 2025 outflows."},
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
