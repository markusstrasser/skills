#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "append-skill-memento.sh"


class AppendSkillMementoTests(unittest.TestCase):
    def _run(self, initial: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "research"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(initial, encoding="utf-8")
            proc = subprocess.run(
                [str(HOOK), "research", "fetch transport timed out"],
                text=True,
                capture_output=True,
                env={**os.environ, "SKILLS_DIR": tmp},
                check=False,
            )
            return proc, skill_md.read_text(encoding="utf-8")

    def test_appends_when_known_issues_is_final_section(self):
        proc, updated = self._run("# Research\n\n## Known Issues\n\n- old\n")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("fetch transport timed out", updated)
        self.assertGreater(updated.index("fetch transport timed out"), updated.index("- old"))

    def test_inserts_before_following_section(self):
        proc, updated = self._run(
            "# Research\n\n## Known Issues\n\n- old\n\n## References\n\n- ref\n"
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(updated.index("fetch transport timed out"), updated.index("## References"))
        self.assertGreater(updated.index("fetch transport timed out"), updated.index("- old"))


if __name__ == "__main__":
    unittest.main()
