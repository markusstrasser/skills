#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from pretool_f16_midwrite_crawl_guard import (  # noqa: E402
    evaluate,
    is_full_dag_crawl,
    is_genomics_stage_writer,
)


def _payload(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _stage_app(*, state: str = "ephemeral", tasks: str = "1") -> dict[str, str]:
    return {
        "app_id": "ap-stage",
        "description": "deepvariant--gcpid-encoded-identity",
        "state": state,
        "tasks": tasks,
    }


class F16GuardTests(unittest.TestCase):
    def test_crawl_classifier_distinguishes_list_free_and_scoped_commands(self) -> None:
        self.assertTrue(is_full_dag_crawl("just sample-remediation syn4sr --json"))
        self.assertTrue(
            is_full_dag_crawl(
                "uv run python3 scripts/modal_sync_results.py pull syn4sr --all"
            )
        )
        self.assertFalse(
            is_full_dag_crawl(
                "just sample-remediation syn4sr --target deepvariant"
            )
        )
        self.assertFalse(
            is_full_dag_crawl(
                "uv run python3 scripts/modal_sync_results.py pull syn4sr --all "
                "--summaries-only"
            )
        )
        self.assertFalse(
            is_full_dag_crawl(
                "uv run python3 scripts/modal_sync_results.py freshness "
                "--sample syn4sr --all"
            )
        )

    def test_writer_requires_canonical_identity_and_positive_task_count(self) -> None:
        self.assertTrue(is_genomics_stage_writer(_stage_app()))
        self.assertTrue(
            is_genomics_stage_writer(_stage_app(state="ephemeral (detached)"))
        )
        self.assertFalse(is_genomics_stage_writer(_stage_app(tasks="0")))
        self.assertFalse(is_genomics_stage_writer(_stage_app(state="stopped")))
        self.assertFalse(
            is_genomics_stage_writer(
                {
                    "app_id": "ap-unrelated",
                    "description": "arc-agi-duck-sft",
                    "state": "ephemeral",
                    "tasks": "1",
                }
            )
        )

    def test_unrelated_workspace_job_does_not_block_genomics_crawl(self) -> None:
        rows = [
            {
                "app_id": "ap-unrelated",
                "description": "arc-agi-duck-sft",
                "state": "ephemeral",
                "tasks": "1",
            },
            _stage_app(state="ephemeral (detached)", tasks="0"),
        ]
        decision = evaluate(
            _payload("just sample-remediation syn4sr --json"), app_loader=lambda: rows
        )
        self.assertFalse(decision.blocked)
        self.assertEqual(decision.writers, ())

    def test_task_bearing_detached_stage_app_blocks(self) -> None:
        writer = _stage_app(state="ephemeral (detached)", tasks="1")
        decision = evaluate(
            _payload("just sample-remediation syn4sr --json"),
            app_loader=lambda: [writer],
        )
        self.assertTrue(decision.blocked)
        self.assertEqual(decision.writers, (writer,))

    def test_modal_inventory_failure_is_fail_open(self) -> None:
        decision = evaluate(
            _payload("just sample-remediation syn4sr --json"), app_loader=lambda: None
        )
        self.assertFalse(decision.blocked)


if __name__ == "__main__":
    unittest.main()
