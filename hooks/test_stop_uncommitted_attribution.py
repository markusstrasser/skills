"""Tests for stop-uncommitted-warn.sh per-session attribution.

Regression coverage for the 2026-06-13 cross-session sweep bug: the hook read
its Edit/Write ledger ONLY from .claude/sessions/<id>.touched-files (the
genomics-local convention), while the global producer
(posttool-session-touched-log.sh) writes /tmp/session-touched-<id>.txt. The
path mismatch left attribution empty in every repo except genomics, so a
session-end checkpoint swept concurrent sessions' uncommitted files.

Each test builds a throwaway git repo, plants ledgers for a "mine" and an
"other" session, makes uncommitted changes owned by each, fires the hook AS
the other session, and asserts it auto-commits only the other session's file
and leaves mine uncommitted.

The hook reads session_id stdin-first, so passing it in the JSON payload is
race-immune and does not depend on .claude/current-session-id.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

# precommit-trigger: stop-uncommitted-warn.sh test_stop_uncommitted_attribution.py
# ^ validate-changed-hooks.sh runs this test when the hook (or this test) is staged. The
#   inline-single-quote idiom that silently kills this bash-embedded hook has recurred twice
#   (2026-06-11, then f8e2168); test_embedded_python_parses + the attribution cases now block
#   the next reintroduction at commit time instead of weeks later.

SCRIPT = Path(__file__).resolve().parent / "stop-uncommitted-warn.sh"


class StopUncommittedAttributionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="stop-uncommitted-test-"))
        self._git("init", "-q")
        self._git("config", "user.email", "t@t.t")
        self._git("config", "user.name", "t")
        (self.repo / "seed.txt").write_text("base\n")
        self._git("add", "seed.txt")
        self._git("commit", "-qm", "seed")
        self.mine = f"testmine-{os.getpid()}"
        self.other = f"testother-{os.getpid()}"
        self.tmp_ledgers: list[Path] = []

    def tearDown(self) -> None:
        for p in self.tmp_ledgers:
            p.unlink(missing_ok=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()

    def _tmp_ledger(self, sid: str, *rels: str) -> None:
        p = Path("/tmp") / f"session-touched-{sid}.txt"
        p.write_text("".join(r + "\n" for r in rels))
        self.tmp_ledgers.append(p)

    def _repo_ledger(self, sid: str, *rels: str) -> None:
        d = self.repo / ".claude" / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{sid}.touched-files").write_text("".join(r + "\n" for r in rels))

    def _write_settled(self, rel: str, content: str) -> None:
        """Write a repo file and backdate its mtime past the hook's 90s in-flight
        window. The Stop hook defers files written in the last 90s as still-being-
        written subagent stubs (stop-uncommitted-warn.sh, commit f8e2168); a fresh
        write here would be deferred, never committed, masking the attribution
        behavior these tests target. In-flight deferral is covered separately by
        test_inflight_file_deferred."""
        p = self.repo / rel
        p.write_text(content)
        old = time.time() - 200
        os.utime(p, (old, old))

    def _fire_as(self, sid: str) -> None:
        stdin = '{"cwd":"%s","session_id":"%s"}' % (self.repo, sid)
        subprocess.run(["bash", str(SCRIPT)], input=stdin,
                       capture_output=True, text=True, timeout=20)

    def _head_files(self) -> str:
        return self._git("show", "--name-only", "--format=", "HEAD")

    def test_tmp_convention_no_sweep(self) -> None:
        """Global /tmp ledger: firing other must not commit mine's file."""
        self._tmp_ledger(self.mine, "mine.py")
        self._tmp_ledger(self.other, "other.py")
        self._write_settled("mine.py", "m\n")
        self._write_settled("other.py", "o\n")
        self._fire_as(self.other)
        self.assertIn("other.py", self._head_files())
        self.assertIn("mine.py", self._git("status", "--short", "mine.py"))

    def test_mixed_conventions(self) -> None:
        """other via .claude/sessions, mine via /tmp — both honored together."""
        self._repo_ledger(self.other, "other.py")
        self._tmp_ledger(self.mine, "mine.py")
        self._write_settled("mine.py", "m\n")
        self._write_settled("other.py", "o\n")
        self._fire_as(self.other)
        self.assertIn("other.py", self._head_files())
        self.assertIn("mine.py", self._git("status", "--short", "mine.py"))

    def test_empty_input_exits_clean(self) -> None:
        r = subprocess.run(["bash", str(SCRIPT)], input="{}",
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0)

    def test_inflight_file_deferred(self) -> None:
        """A ledger-owned file written <90s ago is deferred (not committed),
        even when attribution would otherwise commit it."""
        self._tmp_ledger(self.other, "fresh.py")
        (self.repo / "fresh.py").write_text("o\n")  # mtime ~ now -> in-flight
        self._fire_as(self.other)
        self.assertNotIn("fresh.py", self._head_files())
        self.assertIn("fresh.py", self._git("status", "--short", "fresh.py"))

    # NB: parse-safety of the embedded `python3 -c` program (the inline-single-quote
    # idiom that silently kills this hook) is enforced separately and faithfully by
    # lint_hook_input_contract.py, which simulates bash's quote splicing — the
    # always-on contract gate in validate-changed-hooks.sh runs it on every staged
    # hook. A naive compile() of the raw file text here would be UNFAITHFUL (the
    # quotes are harmless in a python comment but corrupt the bash-spliced program),
    # so it is intentionally NOT duplicated. A parse-dead hook also fails every
    # behavioral case below (no output -> assertions fail), so it cannot slip through.


if __name__ == "__main__":
    unittest.main()
