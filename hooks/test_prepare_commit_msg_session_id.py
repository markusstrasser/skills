"""Regression tests for race-safe commit provenance across Claude and Codex."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "prepare-commit-msg-session-id.sh"


class PrepareCommitMessageSessionIdTest(unittest.TestCase):
    def run_hook(
        self,
        *,
        claude_id: str | None,
        codex_id: str | None,
        shared_id: str,
        claude_code_id: str | None = None,
    ) -> str:
        with tempfile.TemporaryDirectory(prefix="session-trailer-") as raw:
            root = Path(raw)
            (root / ".claude").mkdir()
            (root / ".claude" / "current-session-id").write_text(shared_id)
            message = root / "COMMIT_EDITMSG"
            message.write_text("[test] Exercise trailer\n")
            env = os.environ.copy()
            # A test run from inside a Claude session inherits real ids; clear all three.
            for name in ("CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID"):
                env.pop(name, None)
            if claude_id is not None:
                env["CLAUDE_SESSION_ID"] = claude_id
            if claude_code_id is not None:
                env["CLAUDE_CODE_SESSION_ID"] = claude_code_id
            if codex_id is not None:
                env["CODEX_THREAD_ID"] = codex_id
            subprocess.run(
                ["bash", str(SCRIPT), str(message), "message"],
                cwd=root,
                env=env,
                check=True,
            )
            return message.read_text()

    def test_codex_thread_beats_shared_peer_file(self) -> None:
        message = self.run_hook(claude_id=None, codex_id="codex-own", shared_id="peer")
        self.assertTrue(message.endswith("Session-ID: codex-own\n"))
        self.assertNotIn("Session-ID: peer", message)

    def test_claude_session_precedes_codex_thread(self) -> None:
        message = self.run_hook(
            claude_id="claude-own", codex_id="codex-own", shared_id="peer"
        )
        self.assertTrue(message.endswith("Session-ID: claude-own\n"))

    def test_shared_file_remains_last_resort(self) -> None:
        message = self.run_hook(claude_id=None, codex_id=None, shared_id="fallback")
        self.assertTrue(message.endswith("Session-ID: fallback\n"))

    def test_hook_process_claude_code_id_beats_shared_peer_file(self) -> None:
        """A Claude hook process (e.g. a Stop-hook auto-checkpoint commit) has only
        CLAUDE_CODE_SESSION_ID; it must stamp that, not whatever a peer last wrote."""
        message = self.run_hook(
            claude_id=None, claude_code_id="hook-own", codex_id=None, shared_id="peer"
        )
        self.assertTrue(message.endswith("Session-ID: hook-own\n"))
        self.assertNotIn("Session-ID: peer", message)

    def test_claude_session_precedes_claude_code_session(self) -> None:
        message = self.run_hook(
            claude_id="shell-own", claude_code_id="hook-own", codex_id="codex-own", shared_id="peer"
        )
        self.assertTrue(message.endswith("Session-ID: shell-own\n"))

    def test_claude_code_session_precedes_codex_thread(self) -> None:
        message = self.run_hook(
            claude_id=None, claude_code_id="hook-own", codex_id="codex-own", shared_id="peer"
        )
        self.assertTrue(message.endswith("Session-ID: hook-own\n"))


if __name__ == "__main__":
    unittest.main()
