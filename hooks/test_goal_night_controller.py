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
import subprocess
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
