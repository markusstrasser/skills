from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "integration_audit.py"
SPEC = importlib.util.spec_from_file_location("integration_audit", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class IntegrationAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "T")
        self.review = self.repo / ".model-review" / "test-review"
        self.review.mkdir(parents=True)
        (self.repo / "foo.py").write_text("x = 1\n")
        git(self.repo, "add", "foo.py")
        git(self.repo, "commit", "-m", "init")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_review(self, title: str, fix: str, verdict: str = "HALLUCINATED") -> None:
        findings = {
            "findings": [
                {
                    "id": 1,
                    "title": title,
                    "fix": fix,
                    "file": "foo.py",
                    "severity": "high",
                    "source_model": "gemini-3.5-flash",
                }
            ]
        }
        (self.review / "findings.json").write_text(json.dumps(findings))
        (self.review / "verified-disposition.md").write_text(
            f"| 1 | {verdict} | {title} | notes |\n"
        )

    def test_pass_when_no_hallucinated(self) -> None:
        self._write_review("real bug", "fix the boundary", verdict="CONFIRMED")
        r = mod.audit(self.review, self.repo, base=None, head=None, plan_path=None)
        self.assertTrue(r.ok)

    def test_fail_when_fix_phrasing_in_diff(self) -> None:
        self._write_review(
            "fake bug",
            "Emit excluded business items to a separate migration file",
        )
        (self.repo / "foo.py").write_text(
            "# emit excluded business items to a separate migration file\nx = 2\n"
        )
        r = mod.audit(self.review, self.repo, base=None, head=None, plan_path=None)
        self.assertFalse(r.ok)
        self.assertTrue(any("fix phrasing" in f for f in r.failures))

    def test_fail_when_title_in_commit(self) -> None:
        title = "Gmail body extraction lacks HTML-to-text fallback"
        self._write_review(title, "add html parser")
        (self.repo / "foo.py").write_text("x = 2\n")
        git(self.repo, "add", "foo.py")
        git(self.repo, "commit", "-m", f"address review: {title}")
        r = mod.audit(self.review, self.repo, base="HEAD~1", head="HEAD", plan_path=None)
        self.assertFalse(r.ok)


if __name__ == "__main__":
    unittest.main()
