"""Tests for stop-unsupported-completion.sh shadow-mode predicate.

Runs the hook in an isolated HOME so shadow/error logs don't pollute the
real ~/.claude dir, then inspects the JSONL output to verify classification
behavior for each case.

Coverage targets the branch-classes flagged in
.model-review/2026-04-11-bias-plan-close-89878c/ finding 8:
- terse single-verb success claim (post-fix: must fire)
- success + structural evidence markers (must not fire)
- success + prediction language (must not fire)
- success + weak hedging only (should/would — must fire post-fix)
- "I ran out of time" false-negative case (must fire post-fix)
- malformed JSON (must log to error file, exit cleanly)
- stop_hook_active bypass (must skip silently)
- no success words (must skip silently)
- 'succeeded' form (must fire)
- numeric test citation (must not fire)
- empty last_assistant_message (must skip silently)
- short message "Fixed." (must fire — len<20 exclusion removed)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "stop-unsupported-completion.sh"


class StopUnsupportedCompletionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="stop-ucomp-test-"))
        (self.tmp / ".claude").mkdir(parents=True, exist_ok=True)
        self.shadow = self.tmp / ".claude" / "unsupported-completion-shadow.jsonl"
        self.err = self.tmp / ".claude" / "unsupported-completion-errors.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_hook(self, stdin: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(self.tmp)
        # Ensure CLAUDE_SESSION_ID does not leak in from the live session — tests
        # want the session_id from the JSON payload, not the real session.
        env.pop("CLAUDE_SESSION_ID", None)
        env.pop("CLAUDE_CWD", None)
        return subprocess.run(
            ["bash", str(SCRIPT)],
            input=stdin,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def shadow_entries(self) -> list[dict]:
        if not self.shadow.exists():
            return []
        return [json.loads(l) for l in self.shadow.read_text().splitlines() if l.strip()]

    def error_entries(self) -> list[dict]:
        if not self.err.exists():
            return []
        return [json.loads(l) for l in self.err.read_text().splitlines() if l.strip()]

    # ------------------------------------------------------------------
    # Must-fire cases (would_fire=True)
    # ------------------------------------------------------------------

    def test_terse_single_success_claim_fires(self) -> None:
        """'Fixed.' — single verb, no evidence. Previously blocked by len<20 AND success_hits>=2."""
        self.run_hook(json.dumps({"last_assistant_message": "Fixed."}))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["would_fire"])
        self.assertEqual(entries[0]["success_hits"], 1)

    def test_weak_hedging_only_fires(self) -> None:
        """'should'/'would' are not evidence. Must not suppress."""
        self.run_hook(json.dumps({
            "last_assistant_message": "This should be fixed now. It would have been worse otherwise."
        }))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["would_fire"])

    def test_ran_out_of_time_fires(self) -> None:
        """'I ran out of time' previously matched \\bran\\b as evidence. Must fire post-fix."""
        self.run_hook(json.dumps({
            "last_assistant_message": "I ran out of time. The fix works now."
        }))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["would_fire"])

    def test_succeeded_form_fires(self) -> None:
        """'succeed'/'succeeded' was previously missed by succe(ss|eded|eds)."""
        self.run_hook(json.dumps({
            "last_assistant_message": "The deployment succeeded without incident."
        }))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["would_fire"])

    # ------------------------------------------------------------------
    # Must-not-fire cases (would_fire=False, but logged)
    # ------------------------------------------------------------------

    def test_success_with_structural_evidence_suppresses(self) -> None:
        """pytest + stdout + 'green' are structural evidence markers."""
        self.run_hook(json.dumps({
            "last_assistant_message": "Fixed the bug. Ran pytest, 12 tests passed with stdout showing all green."
        }))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0]["would_fire"])
        self.assertGreaterEqual(entries[0]["evidence_hits"], 1)

    def test_success_with_prediction_suppresses(self) -> None:
        """'expected'/'previously' indicate temporal framing that outcome bias lacks."""
        self.run_hook(json.dumps({
            "last_assistant_message": "As expected, the refactor works. Previously we had a bug in the loop."
        }))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0]["would_fire"])
        self.assertGreaterEqual(entries[0]["prediction_hits"], 1)

    def test_numeric_test_result_suppresses(self) -> None:
        """'27 tests' pattern is structural evidence."""
        self.run_hook(json.dumps({
            "last_assistant_message": "All 27 tests pass. Deployment complete."
        }))
        entries = self.shadow_entries()
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0]["would_fire"])

    # ------------------------------------------------------------------
    # Skip cases (no log entry at all)
    # ------------------------------------------------------------------

    def test_no_success_words_skips(self) -> None:
        self.run_hook(json.dumps({
            "last_assistant_message": "Reading the config file before making changes."
        }))
        self.assertEqual(self.shadow_entries(), [])

    def test_stop_hook_active_skips(self) -> None:
        self.run_hook(json.dumps({
            "last_assistant_message": "Fixed, works, done",
            "stop_hook_active": True,
        }))
        self.assertEqual(self.shadow_entries(), [])

    def test_empty_message_skips(self) -> None:
        self.run_hook(json.dumps({"last_assistant_message": ""}))
        self.assertEqual(self.shadow_entries(), [])

    # ------------------------------------------------------------------
    # Error-path coverage
    # ------------------------------------------------------------------

    def test_malformed_json_logs_to_error_file(self) -> None:
        """Was previously silent under 2>/dev/null. Must now write to error log."""
        result = self.run_hook("not-json")
        self.assertEqual(result.returncode, 0)  # fail-open preserved
        errors = self.error_entries()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["stage"], "input_parse")
        self.assertIn("JSONDecodeError", errors[0]["error"])

    def test_exit_code_always_zero(self) -> None:
        """Fail-open: hook must never block Stop."""
        for payload in [
            "not-json",
            json.dumps({"last_assistant_message": "Fixed."}),
            json.dumps({"last_assistant_message": ""}),
            "",
        ]:
            result = self.run_hook(payload)
            self.assertEqual(result.returncode, 0, f"non-zero exit on payload: {payload!r}")


if __name__ == "__main__":
    unittest.main()
