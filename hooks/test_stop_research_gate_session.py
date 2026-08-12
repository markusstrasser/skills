"""Regression: stop-research-gate must not inherit .claude/current-session-id.

Grok (and any Stop caller with an empty stdin session_id) used to load the
shared Claude current-session-id, pick up that peer's base_sha, and block on
committed untagged research the current session never wrote.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOK = Path(__file__).resolve().parent / "stop-research-gate.sh"
PEER = "peer-session-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _run_hook(cwd: Path, payload: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    merged["RESEARCH_PATHS"] = "health/research/"
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=cwd,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=20,
        env=merged,
    )


class StopResearchGateSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="research-gate-")
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name) / "repo"
        self.cwd.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.cwd, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.cwd, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.cwd, check=True)
        (self.cwd / "README.md").write_text("root\n")
        subprocess.run(["git", "add", "README.md"], cwd=self.cwd, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.cwd, check=True)
        self.base = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.cwd, text=True
        ).strip()

        research = self.cwd / "health" / "research"
        research.mkdir(parents=True)
        untagged = research / "untagged.md"
        untagged.write_text("# Audit\n\nA substantive claim with no provenance tag.\n")
        # The gate defers files with mtime < 900s (in-flight drafts). Age this
        # past that window so a committed memo is judged, not deferred.
        aged = os.path.getmtime(untagged) - 1000
        os.utime(untagged, (aged, aged))
        subprocess.run(["git", "add", "health/research/untagged.md"], cwd=self.cwd, check=True)
        subprocess.run(["git", "commit", "-qm", "add untagged research"], cwd=self.cwd, check=True)
        os.utime(untagged, (aged, aged))

        claude = self.cwd / ".claude"
        claude.mkdir()
        (claude / "current-session-id").write_text(PEER)

        self.base_sha_path = Path(f"/tmp/session-base-sha-{PEER}.txt")
        self.baseline_path = Path(f"/tmp/session-baseline-{PEER}.txt")
        self.touched_path = Path(f"/tmp/session-touched-{PEER}.txt")
        self.base_sha_path.write_text(self.base)
        self.baseline_path.write_text("")
        self.addCleanup(self._cleanup_tmp)

    def _cleanup_tmp(self) -> None:
        for path in (self.base_sha_path, self.baseline_path, self.touched_path):
            path.unlink(missing_ok=True)

    def test_empty_stdin_session_id_does_not_inherit_peer_baseline(self) -> None:
        result = _run_hook(self.cwd, {"cwd": str(self.cwd)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("BLOCKED:", result.stderr)

    def test_owner_session_still_blocks_its_own_untagged_commit(self) -> None:
        result = _run_hook(self.cwd, {"cwd": str(self.cwd), "session_id": PEER})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("untagged.md", result.stderr)

    def test_empty_stdin_still_blocks_worktree_dirty_untagged_research(self) -> None:
        dirty = self.cwd / "health" / "research" / "dirty.md"
        dirty.write_text("# Draft\n\nAnother unsourced substantive claim.\n")
        aged = os.path.getmtime(dirty) - 1000
        os.utime(dirty, (aged, aged))
        result = _run_hook(self.cwd, {"cwd": str(self.cwd)})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("dirty.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
