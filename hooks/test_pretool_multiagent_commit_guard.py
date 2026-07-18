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


def _run_guard(
    command: str,
    *,
    process_cwd: Path,
    tool_workdir: Path,
    fake_bin: Path,
    peer_count: int = 1,
):
    payload = {
        "tool_input": {
            "command": command,
            "workdir": str(tool_workdir),
        }
    }
    peer_counter = fake_bin / "peer-session-count"
    peer_counter.write_text(f"#!/bin/sh\nprintf '{peer_count}\\n'\n", encoding="utf-8")
    peer_counter.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "PEER_SESSION_COUNT_BIN": str(peer_counter),
    }
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
            main_reason = json.loads(main_commit.stdout)["reason"]
            self.assertIn(
                "1 peer Claude session(s) share this repository checkout",
                main_reason,
            )
            self.assertIn(
                "Git target classification: shared/main checkout (not a linked worktree)",
                main_reason,
            )
            self.assertNotIn("claude processes active in main repo", main_reason)

            no_repo_peer = _run_guard(
                "git commit -m safe",
                process_cwd=repo,
                tool_workdir=repo,
                fake_bin=fake_bin,
                peer_count=0,
            )
            self.assertEqual(
                no_repo_peer.returncode,
                0,
                no_repo_peer.stdout + no_repo_peer.stderr,
            )

            main_patch_add = _run_guard(
                f"git -C {repo} add -p tracked.txt",
                process_cwd=worktree,
                tool_workdir=worktree,
                fake_bin=fake_bin,
            )
            self.assertEqual(main_patch_add.returncode, 2)
            git_c_reason = json.loads(main_patch_add.stdout)["reason"]
            self.assertIn("Git target classification: shared/main checkout", git_c_reason)

            worktree_patch_add = _run_guard(
                f"git -C {worktree} add -p tracked.txt",
                process_cwd=repo,
                tool_workdir=repo,
                fake_bin=fake_bin,
            )
            self.assertEqual(worktree_patch_add.returncode, 0)


class TrailingPathspecCommitTests(unittest.TestCase):
    """A trailing `-- <paths>` pathspec (no explicit --only flag) is
    git-semantically identical to --only -- a pathspec given to `git commit`
    with no --only/-i already defaults to --only's behavior (verified via
    `git help commit` and empirically). Before this, ONLY the literal
    --only/--include/-i/-p/--amend flags were allow-listed, so the exact
    form teammate-dispatch-protocol.md / CLAUDE.md teach agents to use
    (`git commit -m "..." -- <paths>`) was needlessly blocked whenever
    peers were present (2026-07-18: "Do not hard-block pathspec'd commits
    (too noisy)")."""

    def _repo(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", cwd=repo)
        _git("config", "user.email", "test@example.com", cwd=repo)
        _git("config", "user.name", "Test", cwd=repo)
        (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        _git("add", "tracked.txt", cwd=repo)
        _git("commit", "-m", "baseline", cwd=repo)
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        return repo, fake_bin

    def test_trailing_pathspec_allowed_with_peers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -m "msg" -- tracked.txt', process_cwd=repo,
                            tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_multiline_message_trailing_pathspec_allowed(self) -> None:
        """The pathspec is invisible to a CMD_FIRST-only check once the
        commit message is multi-line -- this must still be recognized as
        safe (the token-aware check reads the FULL command, not line 1)."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            cmd = 'git commit -m "Subject\n\nBody line 1\nBody line 2" -- tracked.txt'
            r = _run_guard(cmd, process_cwd=repo, tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_git_dash_c_prefix_with_trailing_pathspec_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard(f'git -C {repo} commit -m "msg" -- tracked.txt', process_cwd=repo,
                            tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_bare_commit_still_blocked_with_peers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -m "msg"', process_cwd=repo, tool_workdir=repo,
                            fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 2)
            reason = json.loads(r.stdout)["reason"]
            self.assertIn("--only", reason)
            self.assertIn("git add -p", reason)

    def test_dash_a_with_trailing_pathspec_still_blocked(self) -> None:
        """git itself rejects -a combined with a pathspec ("paths ... with
        -a does not make sense") -- the guard must not advertise it as safe."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -a -m "msg" -- tracked.txt', process_cwd=repo,
                            tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_bare_dot_pathspec_still_blocked(self) -> None:
        """A trailing `.` pathspec sweeps the whole cwd -- same hazard class
        as `git add .`, must not be treated as scoped."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -m "msg" -- .', process_cwd=repo,
                            tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_realistic_false_positive_message_still_blocked(self) -> None:
        """Message literally ends in ' -- old approach' (this repo's own
        `Rejected: ...` trailer convention, typed with -- instead of the
        documented em-dash) with NO real trailing pathspec. A naive
        end-of-string regex treated this as a safe pathspec'd commit during
        development -- shlex-based tokenization must not repeat that,
        because the quoted -m message is ONE token, not a real `--`
        separator."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            cmd = 'git commit -m "Subject\n\nRejected: -- old approach"'
            r = _run_guard(cmd, process_cwd=repo, tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_unbalanced_quote_still_blocked(self) -> None:
        """A command shlex cannot parse (e.g. an odd number of quotes) must
        fail CLOSED (still blocked), never be waved through as "safe"."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -m "broken quote', process_cwd=repo,
                            tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_reason_json_always_valid_and_mentions_peer_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -m "msg"', process_cwd=repo, tool_workdir=repo,
                            fake_bin=fake_bin, peer_count=3)
            parsed = json.loads(r.stdout)  # raises if not valid JSON
            self.assertEqual(parsed["decision"], "block")
            self.assertIn("3 peer Claude session(s)", parsed["reason"])

    def test_only_flag_form_still_allowed_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit --only -m "msg" -- tracked.txt', process_cwd=repo,
                            tool_workdir=repo, fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_zero_peers_bare_commit_still_allowed_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, fake_bin = self._repo(Path(tmp))
            r = _run_guard('git commit -m "msg"', process_cwd=repo, tool_workdir=repo,
                            fake_bin=fake_bin, peer_count=0)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_merge_in_progress_bare_commit_still_allowed(self) -> None:
        """MERGE_HEAD carve-out (git forbids --only during a merge) must
        still work unchanged -- unaffected by the trailing-pathspec check,
        which never even runs for a bare `git commit -m msg` with no
        pathspec at all."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo, fake_bin = self._repo(tmp_path)
            _git("checkout", "-b", "other", cwd=repo)
            (repo / "tracked.txt").write_text("other\n", encoding="utf-8")
            _git("commit", "-am", "other", cwd=repo)
            _git("checkout", "main", cwd=repo)
            (repo / "tracked.txt").write_text("mainside\n", encoding="utf-8")
            _git("commit", "-am", "mainside", cwd=repo)
            subprocess.run(["git", "merge", "other"], cwd=repo, capture_output=True, text=True)
            self.assertTrue((repo / ".git" / "MERGE_HEAD").exists())
            r = _run_guard('git commit -m "merge"', process_cwd=repo, tool_workdir=repo,
                            fake_bin=fake_bin, peer_count=1)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
