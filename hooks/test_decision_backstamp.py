"""posttool-decision-backstamp.sh stamps a target ADR only on an EXACT flip relation.

2026-09-23 misfire watch: 4 of 5 stamps came from partial supersessions
(`supersedes_scope`, `supersedes_rationale_of`, a prose `**Supersedes (for phenome):**`)
and declared the whole target ADR "NOT a current direction".
"""

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name("posttool-decision-backstamp.sh")
TARGET = "2026-01-01-old-direction"


def run_hook(tmp_path: Path, new_adr_body: str) -> str:
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    target = decisions / f"{TARGET}.md"
    target.write_text("---\nid: old\n---\n# Old direction\n")
    new = decisions / "2026-02-01-new-direction.md"
    new.write_text(new_adr_body)
    envelope = {"tool_name": "Write", "tool_input": {"file_path": str(new)}}
    subprocess.run(["bash", str(HOOK)], input=json.dumps(envelope), text=True,
                   capture_output=True, check=True, timeout=20)
    return target.read_text()


def relations(rel_type: str) -> str:
    return f"---\nid: new\nrelations:\n  - type: {rel_type}\n    target: {TARGET}\n---\n# New\n"


@pytest.mark.parametrize("rel_type", ["supersedes", "retires", "reverses_premise"])
def test_exact_flip_relation_stamps_target(tmp_path: Path, rel_type: str) -> None:
    assert "Superseded-by [[new]]" in run_hook(tmp_path, relations(rel_type))


@pytest.mark.parametrize("rel_type", ["supersedes_scope", "supersedes_rationale_of", "extends"])
def test_partial_or_non_flip_relation_leaves_target_alone(tmp_path: Path, rel_type: str) -> None:
    assert "Superseded-by" not in run_hook(tmp_path, relations(rel_type))


def test_prose_header_no_longer_stamps(tmp_path: Path) -> None:
    body = f"---\nid: new\n---\n# New\n\n**Supersedes (for phenome):** [[{TARGET}]] one section only.\n"
    assert "Superseded-by" not in run_hook(tmp_path, body)
