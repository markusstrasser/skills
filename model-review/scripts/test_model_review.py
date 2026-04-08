from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
