from __future__ import annotations

import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from shared.skill_manifest import validate_manifest


class SkillManifestTest(unittest.TestCase):
    def test_cli_accepts_relative_and_absolute_manifest_paths(self) -> None:
        root = Path(__file__).resolve().parents[1]
        relative = Path("observe/skill.json")
        outputs = []
        for manifest_path in (relative, root / relative):
            result = subprocess.run(
                [sys.executable, str(root / "scripts/lint_skill_manifests.py"),
                 "--manifest", str(manifest_path)],
                cwd=root, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        self.assertEqual(outputs, ["OK observe/skill.json\n"] * 2)

    def test_cli_reports_invalid_external_manifest_without_traceback(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            manifest_path = Path(td) / "skill.json"
            manifest_path.write_text("{invalid json")
            result = subprocess.run(
                [sys.executable, str(root / "scripts/lint_skill_manifests.py"),
                 "--manifest", "skill.json"],
                cwd=td, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"{manifest_path}: invalid JSON:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_validate_manifest_accepts_known_profile_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "foo").mkdir()
            (root / "foo" / "SKILL.md").write_text("# Foo\n")
            (root / "foo" / "run.py").write_text("print('ok')\n")
            (root / "foo" / "skill.json").write_text(
                """
                {
                  "name": "foo",
                  "kind": "worker",
                  "intent_class": "convergent",
                  "summary": "x",
                  "entrypoint": {"type": "script", "path": "foo/run.py"},
                  "modes": {
                    "main": {
                      "intent_class": "convergent",
                      "requires_packet": true,
                      "requires_gpt": true,
                      "artifacts": ["out.md"]
                    }
                  },
                    "uses": {
                        "dispatch_profiles": ["formal_review"],
                        "packet_builders": ["shared_context_packet"],
                        "artifact_schemas": ["review-coverage.v1"]
                    },
                  "follow_on": ["upgrade"],
                  "references": ["foo/SKILL.md"]
                }
                """.strip()
            )
            issues = validate_manifest(root / "foo" / "skill.json", root)
            self.assertEqual(issues, [])

    def test_validate_manifest_rejects_unknown_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "foo").mkdir()
            (root / "foo" / "SKILL.md").write_text("# Foo\n")
            (root / "foo" / "run.py").write_text("print('ok')\n")
            manifest_path = root / "foo" / "skill.json"
            manifest_path.write_text(
                """
                {
                  "name": "foo",
                  "kind": "worker",
                  "intent_class": "convergent",
                  "summary": "x",
                  "entrypoint": {"type": "script", "path": "foo/run.py"},
                  "modes": {"main": {"intent_class": "convergent", "artifacts": ["out.md"]}},
                  "uses": {"dispatch_profiles": ["not_real"], "packet_builders": [], "artifact_schemas": []},
                  "follow_on": [],
                  "references": ["foo/SKILL.md"]
                }
                """.strip()
            )
            issues = validate_manifest(manifest_path, root)
            self.assertTrue(any("unknown dispatch profile" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
