from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_PATH = SCRIPT_DIR / "llm-budget-report.py"
SPEC = importlib.util.spec_from_file_location("llm_budget_report_script", REPORT_PATH)
assert SPEC is not None and SPEC.loader is not None
llm_budget_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(llm_budget_report)


class LlmBudgetReportTest(unittest.TestCase):
    def test_build_report_groups_profiles_and_recommends_budget(self) -> None:
        report = llm_budget_report.build_report(
            [
                {
                    "requested_profile": "gpt_general",
                    "status": "ok",
                    "context_token_estimate": 8000,
                    "usage": {"prompt_tokens": 7000, "completion_tokens": 300, "total_tokens": 7300},
                },
                {
                    "requested_profile": "gpt_general",
                    "status": "ok",
                    "context_token_estimate": 12000,
                    "usage": {"prompt_tokens": 10000, "completion_tokens": 400, "total_tokens": 10400},
                },
            ]
        )

        stats = report["profiles"]["gpt_general"]
        self.assertEqual(stats["samples"], 2)
        self.assertEqual(stats["configured_input_limit"], 120000)
        self.assertLessEqual(stats["recommended_safe_input_budget"], 120000)
        self.assertGreaterEqual(stats["recommended_safe_input_budget"], 12000)


if __name__ == "__main__":
    unittest.main()
