from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_REVIEW_PATH = SCRIPT_DIR / "model-review.py"
SPEC = importlib.util.spec_from_file_location("model_review_script", MODEL_REVIEW_PATH)
assert SPEC is not None and SPEC.loader is not None
model_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model_review)


class FakePopen:
    calls: list[tuple[str | None, str, str]] = []
    responses: dict[tuple[str, str], list[dict[str, object]]] = {}

    def __init__(self, cmd, env=None, stdout=None, stderr=None):
        self.cmd = cmd
        self.returncode = None
        self.output_path = Path(cmd[cmd.index("-o") + 1])
        self.model = cmd[cmd.index("-m") + 1]
        self.provider = cmd[cmd.index("-p") + 1] if "-p" in cmd else None
        key = (self.model, self.output_path.name)
        queue = self.responses.get(key, [])
        if not queue:
            raise AssertionError(f"unexpected command: {cmd}")
        self.response = queue.pop(0)
        self.calls.append((self.provider, self.model, self.output_path.name))

    def communicate(self):
        self.returncode = int(self.response["rc"])
        content = self.response.get("content")
        if content is None:
            self.output_path.unlink(missing_ok=True)
        else:
            self.output_path.write_text(str(content))
        return b"", str(self.response.get("stderr", "")).encode()


class ModelReviewDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.review_dir = Path(self.temp_dir.name)
        self.ctx_files = {}
        for axis in ("arch", "formal", "domain"):
            ctx = self.review_dir / f"{axis}-context.md"
            ctx.write_text("context")
            self.ctx_files[axis] = ctx

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dispatch_falls_back_after_gemini_rate_limit(self) -> None:
        FakePopen.calls = []
        FakePopen.responses = {
            (model_review.GEMINI_PRO_MODEL, "arch-output.md"): [
                {"rc": 3, "stderr": "503 overloaded", "content": None},
            ],
            ("gpt-5.4", "formal-output.md"): [
                {"rc": 0, "stderr": "", "content": "formal ok"},
            ],
            (model_review.GEMINI_PRO_MODEL, "domain-output.md"): [
                {"rc": 0, "stderr": "", "content": None},
            ],
            (model_review.GEMINI_FLASH_MODEL, "arch-output.md"): [
                {"rc": 0, "stderr": "", "content": "arch fallback"},
            ],
            (model_review.GEMINI_FLASH_MODEL, "domain-output.md"): [
                {"rc": 0, "stderr": "", "content": "domain fallback"},
            ],
        }

        with patch.object(model_review.subprocess, "Popen", FakePopen):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal", "domain"],
                "Review this",
                has_constitution=False,
            )

        self.assertEqual(result["arch"]["requested_model"], model_review.GEMINI_PRO_MODEL)
        self.assertEqual(result["arch"]["model"], model_review.GEMINI_FLASH_MODEL)
        self.assertEqual(result["arch"]["fallback_reason"], "gemini_rate_limit")
        self.assertEqual(result["arch"]["exit_code"], 0)
        self.assertGreater(result["arch"]["size"], 0)

        self.assertEqual(result["domain"]["requested_model"], model_review.GEMINI_PRO_MODEL)
        self.assertEqual(result["domain"]["model"], model_review.GEMINI_FLASH_MODEL)
        self.assertEqual(result["domain"]["fallback_reason"], "gemini_session_rate_limit")
        self.assertEqual(result["domain"]["exit_code"], 0)
        self.assertGreater(result["domain"]["size"], 0)

        self.assertEqual(result["formal"]["model"], "gpt-5.4")
        self.assertEqual(result["formal"]["exit_code"], 0)
        self.assertGreater(result["formal"]["size"], 0)

        self.assertEqual(
            FakePopen.calls,
            [
                (None, model_review.GEMINI_PRO_MODEL, "arch-output.md"),
                ("openai", "gpt-5.4", "formal-output.md"),
                (None, model_review.GEMINI_PRO_MODEL, "domain-output.md"),
                (None, model_review.GEMINI_FLASH_MODEL, "arch-output.md"),
                (None, model_review.GEMINI_FLASH_MODEL, "domain-output.md"),
            ],
        )

    def test_collect_dispatch_failures_flags_zero_byte_outputs(self) -> None:
        dispatch_result = {
            "review_dir": str(self.review_dir),
            "axes": ["formal"],
            "queries": 1,
            "elapsed_seconds": 1.0,
            "formal": {
                "label": "Formal",
                "model": "gpt-5.4",
                "requested_model": "gpt-5.4",
                "exit_code": 0,
                "size": 0,
                "output": str(self.review_dir / "formal-output.md"),
                "stderr": "[llmx:WARN] 0-byte output",
            },
        }

        failures = model_review.collect_dispatch_failures(dispatch_result, self.ctx_files)

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["axis"], "formal")
        self.assertEqual(failures[0]["failure_reason"], "empty_output")
        self.assertEqual(failures[0]["context"], str(self.ctx_files["formal"]))


class ModelReviewMainTest(unittest.TestCase):
    def test_main_returns_nonzero_when_axis_output_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            review_dir = project_dir / ".model-review" / "2026-04-07-empty-axis-abcd12"
            review_dir.mkdir(parents=True)
            ctx_files = {"formal": review_dir / "formal-context.md"}
            ctx_files["formal"].write_text("context")
            dispatch_result = {
                "review_dir": str(review_dir),
                "axes": ["formal"],
                "queries": 1,
                "elapsed_seconds": 1.0,
                "formal": {
                    "label": "Formal",
                    "model": "gpt-5.4",
                    "requested_model": "gpt-5.4",
                    "exit_code": 0,
                    "size": 0,
                    "output": str(review_dir / "formal-output.md"),
                    "stderr": "[llmx:WARN] 0-byte output",
                },
            }

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review, "build_context", return_value=ctx_files), patch.object(
                    model_review, "dispatch", return_value=dispatch_result
                ), patch.object(model_review, "find_constitution", return_value=("", None)), patch.object(
                    model_review.os, "urandom", return_value=b"\xab\xcd\x12"
                ), patch.object(
                    model_review.sys,
                    "argv",
                    [
                        "model-review.py",
                        "--context",
                        str(context_path),
                        "--topic",
                        "empty-axis",
                        "--project",
                        str(project_dir),
                    ],
                ):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            failure_path = project_dir / ".model-review" / "2026-04-07-empty-axis-abcd12" / "dispatch-failures.json"
            self.assertEqual(rc, 2)
            self.assertTrue(failure_path.exists())
            self.assertIn('"failure_reason": "empty_output"', failure_path.read_text())


if __name__ == "__main__":
    unittest.main()
