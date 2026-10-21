"""permission-auto-allow.sh: which Write paths it approves without a prompt."""

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name("permission-auto-allow.sh")


def decision(file_path: str) -> str | None:
    request = json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path}})
    result = subprocess.run(["bash", str(HOOK)], input=request, capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]["decision"]["behavior"]


@pytest.mark.parametrize(
    "file_path",
    ["/repo/.claude/checkpoint.md", "/repo/.claude/checkpoint-339ca089.md", "/repo/.claude/plans/plan.md"],
)
def test_allows_own_checkpoint_briefs_and_plans(file_path):
    assert decision(file_path) == "allow"


@pytest.mark.parametrize(
    "file_path",
    [
        # A glob `*` matches `/`: these once matched */.claude/checkpoint-*.md (2026-10-22).
        "/repo/.claude/checkpoint-x/../../CLAUDE.md",
        "/Users/someone/.claude/checkpoint-a/../../../.zshrc.md",
        "/repo/.claude/plans/../../CLAUDE.md",
        # The hook's own output and curated checkpoints are not briefs.
        "/repo/.claude/checkpoint-auto-aaaaaaaa.md",
        "/repo/.claude/checkpoint-markus-currency.md",
        "/repo/.claude/nested/checkpoint.md/x.md",
    ],
)
def test_leaves_other_paths_to_the_prompt(file_path):
    assert decision(file_path) is None
