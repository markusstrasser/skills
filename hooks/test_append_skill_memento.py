#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "append-skill-memento.sh"


class AppendSkillMementoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skill = self.root / "research"
        self.skill.mkdir()
        self.router = self.skill / "SKILL.md"
        self.original = "---\nname: research\n---\n# Research\n[Issues](references/known-issues.md)\n"
        self.router.write_text(self.original)
        self.history = self.skill / "references" / "known-issues.md"

    def run_helper(self, skill="research", description="fetch transport timed out"):
        return subprocess.run(
            [str(HOOK), skill, description], text=True, capture_output=True,
            env={**os.environ, "SKILLS_DIR": str(self.root)}, check=False,
        )

    def make_history(self, text):
        self.history.parent.mkdir(exist_ok=True)
        self.history.write_text(text)

    def test_appends_preserving_entire_history_and_router(self):
        original = "# Known Issues\n\n- old\n\n## Later correction\n\n- corrected\n"
        self.make_history(original)
        proc = self.run_helper()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        updated = self.history.read_text()
        self.assertTrue(updated.startswith(original))
        self.assertIn("fetch transport timed out", updated[len(original):])
        self.assertEqual(self.router.read_text(), self.original)
        self.assertIn(str(self.history), proc.stdout)

    def test_final_section_and_literal_shell_text_survive_repeated_appends(self):
        self.make_history("# Known Issues\n\n- old\n")
        literal = "$(touch /tmp/never-execute-memento) `literal` %s"
        first = self.run_helper(description=literal)
        second = self.run_helper(description="second issue")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        updated = self.history.read_text()
        self.assertIn(literal, updated)
        self.assertLess(updated.index(literal), updated.index("second issue"))
        self.assertEqual(self.router.read_text(), self.original)

    def test_missing_history_fails_without_mutating_or_creating_files(self):
        proc = self.run_helper()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("create it and link it", proc.stderr)
        self.assertFalse(self.history.exists())
        self.assertEqual(self.router.read_text(), self.original)

    def test_missing_skill_fails_without_mutating_history(self):
        self.make_history("# Known Issues\n")
        self.router.unlink()
        proc = self.run_helper()
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.history.read_text(), "# Known Issues\n")

    def test_skill_name_cannot_escape_root(self):
        self.make_history("# Known Issues\n")
        for name in ("../research", "research/../../outside", "/research"):
            with self.subTest(name=name):
                proc = self.run_helper(skill=name)
                self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.history.read_text(), "# Known Issues\n")
        self.assertEqual(self.router.read_text(), self.original)


if __name__ == "__main__":
    unittest.main()
