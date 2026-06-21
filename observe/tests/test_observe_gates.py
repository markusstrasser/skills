"""Tests for observe_gates_lib — mechanical promotion R/P."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import observe_gates_lib as og  # noqa: E402


class ObserveGatesTest(unittest.TestCase):
    def test_recurrence_gate_fails_single_session(self) -> None:
        v = og.verdict_for_candidate(
            {
                "candidate_id": "c1",
                "sessions": ["abcd1234"],
                "recurrence": 1,
                "checkable": True,
                "summary": "novel hook for widget parser",
            },
            manifest={"abcd1234"},
            log_text="",
            digest_text="",
            promotions_allowed=True,
        )
        self.assertEqual(v.gates["recurrence"], "fail")
        self.assertIn(v.verdict, ("needs_evidence", "suppress"))

    def test_promote_when_gates_pass(self) -> None:
        v = og.verdict_for_candidate(
            {
                "candidate_id": "c2",
                "sessions": ["abcd1234", "efgh5678"],
                "recurrence": 3,
                "checkable": True,
                "summary": "novel zzyxquatch parser failure",
                "dedupe_status": "novel",
            },
            manifest={"abcd1234", "efgh5678"},
            log_text="",
            digest_text="",
            promotions_allowed=True,
        )
        self.assertEqual(v.verdict, "promote")

    def test_existing_coverage_routes_to_obs(self) -> None:
        v = og.verdict_for_candidate(
            {
                "candidate_id": "c3",
                "sessions": ["abcd1234", "efgh5678"],
                "recurrence": 3,
                "checkable": True,
                "summary": "bare python3 duckdb crash",
                "existing_coverage_match": "pretool-uv-python-guard",
            },
            manifest={"abcd1234", "efgh5678"},
            log_text="pretool-uv-python-guard already ships",
            digest_text="",
            promotions_allowed=True,
        )
        self.assertEqual(v.verdict, "obs")

    def test_indexer_blocks_agentlogs_mode(self) -> None:
        v = og.verdict_for_candidate(
            {
                "candidate_id": "c4",
                "mode": "failures",
                "sessions": ["abcd1234", "efgh5678"],
                "recurrence": 3,
                "checkable": True,
                "summary": "missing-module duckdb",
            },
            manifest={"abcd1234", "efgh5678"},
            log_text="",
            digest_text="",
            promotions_allowed=False,
        )
        self.assertEqual(v.gates["indexer_health"], "fail")

    def test_saturation_detects_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observe_base = root / "artifacts" / "observe"
            prior = observe_base / "prior-run"
            prior.mkdir(parents=True)
            cur = observe_base / "current-run"
            cur.mkdir(parents=True)
            row = {
                "candidate_id": "same-id",
                "summary": "bare python3 duckdb module crash repeated",
            }
            (prior / "candidates.jsonl").write_text(json.dumps(row) + "\n")
            (cur / "candidates.jsonl").write_text(json.dumps(row) + "\n")
            import observe_gates_lib as og_mod

            orig = og_mod.project_root
            og_mod.project_root = lambda: root  # type: ignore
            try:
                sat = og_mod.saturation_check(cur, lookback_runs=3)
            finally:
                og_mod.project_root = orig  # type: ignore
            self.assertTrue(sat["saturated"])
            self.assertGreater(sat["id_overlap"], 0.5)

    def test_scan_tool_failures_invoker_classifier(self) -> None:
        import scan_tool_failures as stf

        self.assertEqual(stf.invoker_kind('{"command":"launchctl list"}', "claude"), "harness")
        self.assertEqual(stf.invoker_kind('{"command":"python3 foo.py"}', "claude"), "interactive_agent")


if __name__ == "__main__":
    unittest.main()
