#!/usr/bin/env python3
"""Behavior tests for the goal-night controller trio.

Covers the three live-fire defects found 2026-07-06 (genomics be0657a9:
91/105 auto-compact attempts blocked AFTER goal-done):
  1. precompact-goal-guard must stand down once goal-done/goal-blocked exists
     (the ritual can never fire again, so blocking starves every compact).
  2. stop-goal-wrapup ownership must gate the goal-done challenges too — a
     peer session in an armed repo is never controlled.
  3. postcompact-goal-rearm must be owner-gated — a peer's compaction must not
     erase the owner's ritual/block state.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = os.path.dirname(os.path.abspath(__file__))
STOP = os.path.join(HOOKS, "stop-goal-wrapup.py")
GUARD = os.path.join(HOOKS, "precompact-goal-guard.py")
REARM = os.path.join(HOOKS, "postcompact-goal-rearm.sh")

OWNER = "11111111-1111-1111-1111-111111111111"
PEER = "22222222-2222-2222-2222-222222222222"


def run_hook(path, payload):
    proc = subprocess.run(
        [path], input=json.dumps(payload), capture_output=True, text=True, timeout=20
    )
    return proc.returncode, proc.stdout


def decision(stdout):
    for line in stdout.splitlines():
        try:
            return json.loads(line).get("decision")
        except Exception:
            continue
    return None


class GoalNightBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.claude = os.path.join(self.cwd, ".claude")
        os.makedirs(self.claude)
        self.addCleanup(self.tmp.cleanup)

    def arm(self, threshold=1, owner: str | None = OWNER):
        content = f"{threshold} {owner}\n" if owner else f"{threshold}\n"
        self.state("goal-run", content)

    def state(self, name, content=""):
        with open(os.path.join(self.claude, name), "w") as f:
            f.write(content)

    def has(self, name):
        return os.path.exists(os.path.join(self.claude, name))

    def payload(self, sid=OWNER, **extra):
        return {"cwd": self.cwd, "session_id": sid, **extra}


class TestPrecompactGuard(GoalNightBase):
    def test_blocks_auto_compact_before_ritual(self):
        self.arm()
        _, out = run_hook(GUARD, self.payload(trigger="auto"))
        self.assertEqual(decision(out), "block")
        self.assertTrue(self.has("goal-compact-blocks"))

    def test_stands_down_after_goal_done(self):
        # The regression: post-done the ritual never fires, so blocking would
        # starve 5 attempts per fill cycle forever.
        self.arm()
        self.state("goal-done")
        _, out = run_hook(GUARD, self.payload(trigger="auto"))
        self.assertIsNone(decision(out))
        self.assertFalse(self.has("goal-compact-blocks"))

    def test_stands_down_after_goal_blocked(self):
        self.arm()
        self.state("goal-blocked")
        _, out = run_hook(GUARD, self.payload(trigger="auto"))
        self.assertIsNone(decision(out))

    def test_peer_session_untouched(self):
        self.arm()
        _, out = run_hook(GUARD, self.payload(sid=PEER, trigger="auto"))
        self.assertIsNone(decision(out))
        self.assertFalse(self.has("goal-compact-blocks"))

    def test_three_token_marker_parses(self):
        # goal-night stamps the window as a 3rd token (resume drivers restore the
        # env from it) — hooks must tolerate it: token 1 threshold, token 2 owner.
        self.state("goal-run", f"1 {OWNER} 500000\n")
        _, out = run_hook(GUARD, self.payload(trigger="auto"))
        self.assertEqual(decision(out), "block")
        _, out = run_hook(GUARD, self.payload(sid=PEER, trigger="auto"))
        self.assertIsNone(decision(out))

    def test_block_cap_then_allow(self):
        self.arm()
        self.state("goal-compact-blocks", "5")
        _, out = run_hook(GUARD, self.payload(trigger="auto"))
        self.assertIsNone(decision(out))
        self.assertFalse(self.has("goal-compact-blocks"))  # reset on allow


class TestStopWrapup(GoalNightBase):
    def test_continuation_fires_for_owner(self):
        self.arm(threshold=10**9)  # ritual threshold unreachable
        _, out = run_hook(STOP, self.payload(transcript_path="/nonexistent"))
        self.assertEqual(decision(out), "block")
        self.assertTrue(self.has("goal-continues"))

    def test_peer_session_untouched(self):
        self.arm(threshold=10**9)
        _, out = run_hook(STOP, self.payload(sid=PEER, transcript_path="/nonexistent"))
        self.assertIsNone(decision(out))
        self.assertFalse(self.has("goal-continues"))

    def test_goal_done_allows_stop(self):
        self.arm(threshold=10**9)
        self.state("goal-done")
        _, out = run_hook(STOP, self.payload(transcript_path="/nonexistent"))
        self.assertIsNone(decision(out))

    def test_peer_never_challenged_on_goal_done(self):
        # Ownership must gate the goal-done challenge gates too. Simulate a repo
        # where the challenge preconditions exist (loop/idea_backlog.py present).
        self.arm(threshold=10**9)
        self.state("goal-done")
        os.makedirs(os.path.join(self.cwd, "loop"))
        with open(os.path.join(self.cwd, "loop", "idea_backlog.py"), "w") as f:
            f.write("raise SystemExit(0)\n")
        _, out = run_hook(STOP, self.payload(sid=PEER, transcript_path="/nonexistent"))
        self.assertIsNone(decision(out))
        self.assertFalse(self.has("goal-done-challenged"))


class TestUnstartedGoal(GoalNightBase):
    """Opt-in .claude/goal-deliverable -> loud UNSTARTED warning on zero deliverable progress."""

    @staticmethod
    def _reason(stdout):
        for line in stdout.splitlines():
            try:
                return json.loads(line).get("reason", "")
            except Exception:
                continue
        return ""

    def test_unstarted_warns_when_deliverable_zero(self):
        self.arm(threshold=10**9)
        self.state("goal-continues", "1")  # n>=1: goal has been continuing
        self.state("goal-deliverable", "echo 0/258")
        _, out = run_hook(STOP, self.payload(transcript_path="/nonexistent"))
        self.assertEqual(decision(out), "block")
        self.assertIn("GOAL UNSTARTED", self._reason(out))
        self.assertIn("0/258", self._reason(out))
        self.assertTrue(self.has("goal-unstarted-warned"))

    def test_no_warn_when_deliverable_has_progress(self):
        self.arm(threshold=10**9)
        self.state("goal-continues", "1")
        self.state("goal-deliverable", "echo 42/258")
        _, out = run_hook(STOP, self.payload(transcript_path="/nonexistent"))
        self.assertEqual(decision(out), "block")
        self.assertNotIn("GOAL UNSTARTED", self._reason(out))
        self.assertFalse(self.has("goal-unstarted-warned"))

    def test_no_warn_without_marker(self):
        self.arm(threshold=10**9)
        self.state("goal-continues", "1")
        _, out = run_hook(STOP, self.payload(transcript_path="/nonexistent"))
        self.assertEqual(decision(out), "block")
        self.assertNotIn("GOAL UNSTARTED", self._reason(out))

    def test_unstarted_fires_once(self):
        self.arm(threshold=10**9)
        self.state("goal-continues", "2")
        self.state("goal-deliverable", "echo 0/258")
        self.state("goal-unstarted-warned", "prev\n")  # already warned
        _, out = run_hook(STOP, self.payload(transcript_path="/nonexistent"))
        self.assertEqual(decision(out), "block")
        self.assertNotIn("GOAL UNSTARTED", self._reason(out))


class TestPostcompactRearm(GoalNightBase):
    def test_owner_compaction_rearms(self):
        self.arm()
        self.state("goal-wrapup-fired", "ctx=1\n")
        self.state("goal-compact-blocks", "3")
        rc, _ = run_hook(REARM, self.payload())
        self.assertEqual(rc, 0)
        self.assertFalse(self.has("goal-wrapup-fired"))
        self.assertFalse(self.has("goal-compact-blocks"))

    def test_peer_compaction_does_not_erase_owner_state(self):
        self.arm()
        self.state("goal-wrapup-fired", "ctx=1\n")
        self.state("goal-compact-blocks", "3")
        rc, _ = run_hook(REARM, self.payload(sid=PEER))
        self.assertEqual(rc, 0)
        self.assertTrue(self.has("goal-wrapup-fired"))
        self.assertTrue(self.has("goal-compact-blocks"))

    def test_legacy_ownerless_marker_rearms_any_session(self):
        self.arm(owner=None)
        self.state("goal-wrapup-fired", "ctx=1\n")
        rc, _ = run_hook(REARM, self.payload(sid=PEER))
        self.assertEqual(rc, 0)
        self.assertFalse(self.has("goal-wrapup-fired"))


class TestMarkerClearList(unittest.TestCase):
    """`just goal-night` must clear every run-scoped marker the hooks read.

    A hook that adds a "did this once already" suppression flag without adding it
    to the recipe's rm -f list disarms itself from the SECOND run onward — the flag
    survives the re-arm, so the guard sees "already handled" forever. That is not
    hypothetical: arc-agi carried goal-done-challenged and goal-done-debt-challenged
    from 2026-07-12 into the run armed 07-13, silently disabling both premature-stop
    challenges (found 2026-07-25). This test fails when a new marker appears in a
    hook until it is classified as run-scoped (add to the recipe) or operator-owned
    (add below), so the two lists cannot drift apart again."""

    # Operator-armed config, deliberately NOT cleared by a re-arm.
    OPERATOR_OWNED = {"goal-deliverable"}
    # Written by the arm step itself, after the clear.
    SELF_WRITTEN = {"goal-run"}

    HOOKS = ("stop-goal-wrapup.py", "precompact-goal-guard.py", "postcompact-goal-rearm.sh")
    JUSTFILE = Path.home() / "Projects" / "agent-infra" / "justfile"

    def _clear_list(self) -> set[str]:
        text = self.JUSTFILE.read_text()
        m = re.search(r"^\s*rm -f (\.claude/goal-\S+(?: \.claude/goal-\S+)*)", text, re.M)
        if m is None:
            self.fail("goal-night rm -f line not found in justfile")
        return {tok.split("/")[-1] for tok in m.group(1).split()}

    # Only FILE references count — a bare `goal-night` in prose or the string
    # "precompact-goal-guard.py" in a docstring is not a marker. Match the two
    # forms the hooks actually use to name one.
    _PY_MARKER = re.compile(r'claude_dir\s*/\s*["\'](goal-[a-z][a-z-]*)["\']')
    _SH_MARKER = re.compile(r'(?:\.claude|\$CLAUDE_DIR|\$\{CLAUDE_DIR\})/(goal-[a-z][a-z-]*)')

    def _markers_read(self) -> set[str]:
        found: set[str] = set()
        here = Path(__file__).resolve().parent
        for name in self.HOOKS:
            p = here / name
            if not p.is_file():
                continue
            text = p.read_text()
            found |= set(self._PY_MARKER.findall(text))
            found |= set(self._SH_MARKER.findall(text))
        return found

    def test_every_marker_is_classified(self):
        read = self._markers_read()
        cleared = self._clear_list()
        unclassified = read - cleared - self.OPERATOR_OWNED - self.SELF_WRITTEN
        self.assertEqual(
            unclassified, set(),
            f"marker(s) read by a goal hook but neither cleared on arm nor declared "
            f"operator-owned: {sorted(unclassified)}. Add to the goal-night rm -f list "
            f"(run state) or to OPERATOR_OWNED (operator config).",
        )

    def test_regression_challenge_flags_are_cleared(self):
        cleared = self._clear_list()
        for m in ("goal-done-challenged", "goal-done-debt-challenged"):
            self.assertIn(m, cleared, f"{m} must be cleared on arm — it is a once-per-run "
                                      "suppression flag; leaving it disarms the guard")


if __name__ == "__main__":
    unittest.main()
