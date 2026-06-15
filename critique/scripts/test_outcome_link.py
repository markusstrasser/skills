from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "outcome_link.py"
SPEC = importlib.util.spec_from_file_location("outcome_link", SCRIPT)
assert SPEC and SPEC.loader
ol = importlib.util.module_from_spec(SPEC)
sys.modules["outcome_link"] = ol
SPEC.loader.exec_module(ol)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class OutcomeLinkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "T")
        (self.repo / "gateway.py").write_text("def drain(): pass\n")
        git(self.repo, "add", "gateway.py")
        git(self.repo, "commit", "-m", "init gateway")
        self.rd = self.repo / ".model-review" / "r1"
        self.rd.mkdir(parents=True)
        findings = {
            "findings": [
                {
                    "id": 1,
                    "title": "widget serializer drops null fields on export",
                    "file": "gateway.py",
                    "fix": "preserve null fields in serializer export",
                    "severity": "high",
                }
            ]
        }
        (self.rd / "findings.json").write_text(json.dumps(findings))
        (self.rd / "verified-disposition.md").write_text(
            "| 1 | CONFIRMED | widget serializer drops null fields on export |\n"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_link_tiers_file_vs_anchor(self) -> None:
        payload = ol.link_findings(self.repo, self.rd)
        row = payload["finding_links"][0]
        self.assertTrue(row["linked_file"])
        self.assertFalse(row["linked_anchor"])
        self.assertFalse(row["linked"])
        self.assertEqual(payload["summary"]["linked_anchor"], 0)
        self.assertEqual(payload["summary"]["linked_file_only"], 1)

    def test_link_findings_touches_commits(self) -> None:
        payload = ol.link_findings(self.repo, self.rd)
        self.assertEqual(payload["summary"]["actionable_findings"], 1)
        self.assertTrue(payload["finding_links"][0]["commits_touching_file"])

    def test_cmd_link_writes_json(self) -> None:
        class Args:
            repo = self.repo
            review_dir = self.rd
            since = None
            json = True

        self.assertEqual(ol.cmd_link(Args), 0)
        data = json.loads((self.rd / "outcome-link.json").read_text())
        self.assertIn("finding_links", data)


if __name__ == "__main__":
    unittest.main()
