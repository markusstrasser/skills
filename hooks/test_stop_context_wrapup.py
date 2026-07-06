#!/usr/bin/env python3
"""Behavior tests for stop-context-wrapup.py — the generic pre-compact
loose-ends nudge (once per fill cycle, self-re-arming, goal-owner-aware)."""
import json
import os
import subprocess
import tempfile
import unittest

HOOKS = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HOOKS, "stop-context-wrapup.py")

SID = "aaaaaaaa-0000-0000-0000-000000000000"
OWNER = "11111111-1111-1111-1111-111111111111"


def decision(stdout):
    for line in stdout.splitlines():
        try:
            return json.loads(line).get("decision")
        except Exception:
            continue
    return None


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "repo")
        self.home = os.path.join(self.tmp.name, "home")
        self.claude = os.path.join(self.cwd, ".claude")
        os.makedirs(self.claude)
        os.makedirs(self.home)
        # Isolate from any real statusline tee for these SIDs.
        for sid in (SID, OWNER):
            self.addCleanup(self._rm_ctxpct, sid)
            self._rm_ctxpct(sid)

    @staticmethod
    def _rm_ctxpct(sid):
        try:
            os.unlink(f"/tmp/claude-ctxpct-{sid}")
        except FileNotFoundError:
            pass

    def write_ctxpct(self, pct, tokens, window, sid=SID):
        with open(f"/tmp/claude-ctxpct-{sid}", "w") as f:
            f.write(f"{pct}|{tokens}|{window}")

    def transcript(self, ctx):
        path = os.path.join(self.tmp.name, "transcript.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"message": {"usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": ctx - 10,
                "cache_creation_input_tokens": 0,
            }}}) + "\n")
        return path

    def fire(self, ctx, sid=SID, window=None):
        env = {**os.environ, "HOME": self.home}
        env.pop("CLAUDE_CODE_AUTO_COMPACT_WINDOW", None)
        if window is not None:
            env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = str(window)
        payload = {"cwd": self.cwd, "session_id": sid,
                   "transcript_path": self.transcript(ctx)}
        proc = subprocess.run([HOOK], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=20, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return decision(proc.stdout)

    def state_file(self):
        return os.path.join(self.home, ".claude", "ctx-wrapup", SID)


class TestContextWrapup(Base):
    def test_fires_at_threshold_default_window(self):
        # default window 200K, MARGIN 45K -> threshold 155K
        self.assertEqual(self.fire(160_000), "block")
        self.assertTrue(os.path.exists(self.state_file()))

    def test_silent_below_threshold(self):
        self.assertIsNone(self.fire(120_000))
        self.assertFalse(os.path.exists(self.state_file()))

    def test_once_per_cycle(self):
        self.assertEqual(self.fire(160_000), "block")
        self.assertIsNone(self.fire(170_000))  # same cycle, already fired

    def test_rearms_after_compaction_drop_and_fires_next_cycle(self):
        self.assertEqual(self.fire(160_000), "block")
        self.assertIsNone(self.fire(60_000))   # ctx fell -> re-armed, below threshold
        self.assertFalse(os.path.exists(self.state_file()))
        self.assertEqual(self.fire(158_000), "block")  # next fill cycle fires

    def test_env_window_raises_threshold(self):
        # window 500K -> threshold 455K; 160K stays silent
        self.assertIsNone(self.fire(160_000, window=500_000))
        self.assertEqual(self.fire(460_000, window=500_000), "block")

    def test_statusline_window_1m_no_misfire(self):
        # Real incident (2026-07-06): 1M sessions nudged at ~17% because the
        # hook assumed 200K. The statusline tee carries the model window.
        self.write_ctxpct(17, 170_000, 1_000_000)
        self.assertIsNone(self.fire(170_000))

    def test_statusline_window_1m_fires_before_native_compact(self):
        # Unconfigured binary on 1M compacts at ~475K (effective 500K window,
        # measured genomics be0657a9) — the nudge must beat it: 500K-45K=455K.
        self.write_ctxpct(46, 460_000, 1_000_000)
        self.assertEqual(self.fire(460_000), "block")

    def test_env_window_beats_statusline(self):
        self.write_ctxpct(17, 170_000, 1_000_000)
        self.assertEqual(self.fire(460_000, window=500_000), "block")

    def test_env_lever_capped_by_model_window(self):
        # A 900K env lever on a 200K-window model can't move the binary past
        # the model window — threshold must stay 200K-relative.
        self.write_ctxpct(80, 160_000, 200_000)
        self.assertEqual(self.fire(160_000, window=900_000), "block")

    def test_settings_auto_compact_window_honored(self):
        with open(os.path.join(self.claude, "settings.json"), "w") as f:
            json.dump({"autoCompactWindow": 300_000}, f)
        self.write_ctxpct(30, 290_000, 1_000_000)
        self.assertIsNone(self.fire(200_000))          # 300K-45K=255K
        self.assertEqual(self.fire(260_000), "block")

    def test_garbage_ctxpct_falls_back_to_default(self):
        with open(f"/tmp/claude-ctxpct-{SID}", "w") as f:
            f.write("not|a|window")
        self.assertEqual(self.fire(160_000), "block")  # default 200K path

    def test_goal_owner_skipped_peer_covered(self):
        with open(os.path.join(self.claude, "goal-run"), "w") as f:
            f.write(f"420000 {OWNER} 500000\n")
        self.assertIsNone(self.fire(160_000, sid=OWNER))   # goal ritual owns it
        self.assertEqual(self.fire(160_000, sid=SID), "block")  # peer still nudged

    def test_ownerless_goal_marker_skips_all(self):
        with open(os.path.join(self.claude, "goal-run"), "w") as f:
            f.write("420000\n")
        self.assertIsNone(self.fire(160_000))

    def test_opt_out_file(self):
        open(os.path.join(self.claude, "ctx-wrapup-off"), "w").close()
        self.assertIsNone(self.fire(160_000))

    def test_unreadable_transcript_silent(self):
        env = {**os.environ, "HOME": self.home}
        payload = {"cwd": self.cwd, "session_id": SID,
                   "transcript_path": "/nonexistent"}
        proc = subprocess.run([HOOK], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=20, env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertIsNone(decision(proc.stdout))


if __name__ == "__main__":
    unittest.main()
