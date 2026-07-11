#!/usr/bin/env python3
"""Target-repository tests for the multi-agent commit guard."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name("pretool-multiagent-commit-guard.sh")


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _run_guard(command: str, *, process_cwd: Path, tool_workdir: Path, fake_bin: Path):
    payload = {
        "tool_input": {
            "command": command,
            "workdir": str(tool_workdir),
        }
    }
    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=process_cwd,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


class MultiAgentCommitGuardTests(unittest.TestCase):
    def test_guard_resolves_linked_worktree_from_tool_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            repo.mkdir()
            _git("init", cwd=repo)
            _git("config", "user.email", "test@example.com", cwd=repo)
            _git("config", "user.name", "Test", cwd=repo)
            (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            _git("add", "tracked.txt", cwd=repo)
            _git("commit", "-m", "baseline", cwd=repo)
            worktree = tmp_path / "linked"
            _git("worktree", "add", "--detach", str(worktree), cwd=repo)

            fake_bin = tmp_path / "bin"
            fake_bin.mkdir()
            fake_pgrep = fake_bin / "pgrep"
            fake_pgrep.write_text("#!/bin/sh\nprintf '101\\n102\\n'\n", encoding="utf-8")
            fake_pgrep.chmod(0o755)

            by_tool_dir = _run_guard(
                "git commit -m isolated",
                process_cwd=repo,
                tool_workdir=worktree,
                fake_bin=fake_bin,
            )
            self.assertEqual(by_tool_dir.returncode, 0, by_tool_dir.stdout + by_tool_dir.stderr)

            by_git_c = _run_guard(
                f"git -C {worktree} commit -m isolated",
                process_cwd=repo,
                tool_workdir=repo,
                fake_bin=fake_bin,
            )
            self.assertEqual(by_git_c.returncode, 0, by_git_c.stdout + by_git_c.stderr)

            main_commit = _run_guard(
                "git commit -m unsafe",
                process_cwd=repo,
                tool_workdir=repo,
                fake_bin=fake_bin,
            )
            self.assertEqual(main_commit.returncode, 2)
            self.assertIn("main repo (not a worktree)", main_commit.stdout)

            main_patch_add = _run_guard(
                f"git -C {repo} add -p tracked.txt",
                process_cwd=worktree,
                tool_workdir=worktree,
                fake_bin=fake_bin,
            )
            self.assertEqual(main_patch_add.returncode, 2)

            worktree_patch_add = _run_guard(
                f"git -C {worktree} add -p tracked.txt",
                process_cwd=repo,
                tool_workdir=repo,
                fake_bin=fake_bin,
            )
            self.assertEqual(worktree_patch_add.returncode, 0)


if __name__ == "__main__":
    unittest.main()
