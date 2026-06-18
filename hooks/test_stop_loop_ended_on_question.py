#!/usr/bin/env python3
"""Tests for stop_loop_ended_on_question — the predicate + the gate (would_fire)."""
import importlib.util
import os
import unittest

_spec = importlib.util.spec_from_file_location(
    "sloq", os.path.join(os.path.dirname(__file__), "stop_loop_ended_on_question.py")
)
sloq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sloq)


class TestEndedOnQuestion(unittest.TestCase):
    def test_plain_trailing_question(self):
        self.assertTrue(sloq.ended_on_question("I did X. Want me to wire the surface too?"))

    def test_question_with_markdown_emphasis(self):
        self.assertTrue(sloq.ended_on_question("Shipped. **Should I also promote it globally?**"))

    def test_statement_does_not_fire(self):
        self.assertFalse(sloq.ended_on_question("Done — committed as abc123. Moving on."))

    def test_rhetorical_answered_question_does_not_fire(self):
        # last sentence ends with '.', not '?'
        self.assertFalse(sloq.ended_on_question("Why pivot the frame? Because tuning harder loops."))

    def test_ends_with_code_fence_does_not_fire(self):
        self.assertFalse(sloq.ended_on_question("Run:\n```\njust loop-health?\n```"))

    def test_question_inside_open_code_fence_does_not_fire(self):
        self.assertFalse(sloq.ended_on_question("Here:\n```\nsqlite> select * from t where x=?"))

    def test_empty(self):
        self.assertFalse(sloq.ended_on_question(""))


class TestGate(unittest.TestCase):
    def test_loop_session_question_would_fire(self):
        rec = sloq.evaluate({
            "last_assistant_message": "Tried the obvious knobs. Which direction do you want?",
            "session_crons": [{"id": "c1", "recurring": True, "prompt": "/dream"}],
            "permission_mode": "default",
        })
        self.assertTrue(rec["would_fire"])

    def test_interactive_question_does_not_fire(self):
        # No session_crons → interactive session → ending on a question is CORRECT, no fire.
        rec = sloq.evaluate({
            "last_assistant_message": "Which direction do you want?",
            "session_crons": [],
            "permission_mode": "default",
        })
        self.assertFalse(rec["would_fire"])
        self.assertTrue(rec["ended_on_question"])  # predicate true, gate suppresses

    def test_loop_statement_does_not_fire(self):
        rec = sloq.evaluate({
            "last_assistant_message": "Advanced the probe, committed. Continuing other fronts.",
            "session_crons": [{"id": "c1"}],
        })
        self.assertFalse(rec["would_fire"])

    def test_continuation_guard(self):
        # stop_hook_active → already continuing → never fire (avoids loops on promotion).
        rec = sloq.evaluate({
            "last_assistant_message": "What next?",
            "session_crons": [{"id": "c1"}],
            "stop_hook_active": True,
        })
        self.assertFalse(rec["would_fire"])


if __name__ == "__main__":
    unittest.main()
