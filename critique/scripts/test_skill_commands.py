"""The critique skill's documented commands must not sync the reviewed project's venv.

2026-10-14, immigration-research: `uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py`,
run from the reviewed repo as the docs said, made uv remove and rebuild that repo's `.venv`.
The scripts need nothing from the project, so every documented call uses `--no-project`.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PROJECT_MODE = re.compile(r"uv run (?!--no-project)[^\n]*\$\{CLAUDE_SKILL_DIR\}")
# history.md preserves superseded commands as provenance.
EXEMPT = {SKILL / "references" / "history.md"}


class SkillCommandTest(unittest.TestCase):
    def test_no_project_mode_uv_runs(self) -> None:
        hits = []
        for path in sorted([*SKILL.rglob("*.md"), *SKILL.glob("scripts/*.py")]):
            if path in EXEMPT or path == Path(__file__).resolve():
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if PROJECT_MODE.search(line):
                    hits.append(f"{path.relative_to(SKILL)}:{n}: {line.strip()}")
        self.assertEqual(hits, [], "use `uv run --no-project python3 ${CLAUDE_SKILL_DIR}/...`")

    def test_pattern_catches_project_mode(self) -> None:
        self.assertTrue(PROJECT_MODE.search("uv run python3 ${CLAUDE_SKILL_DIR}/scripts/x.py"))
        self.assertFalse(PROJECT_MODE.search("uv run --no-project python3 ${CLAUDE_SKILL_DIR}/scripts/x.py"))


if __name__ == "__main__":
    unittest.main()
