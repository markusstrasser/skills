from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.skill_manifest import validate_manifest


class SkillManifestTest(unittest.TestCase):
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
