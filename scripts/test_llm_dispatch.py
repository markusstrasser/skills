from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from shared import llm_dispatch


class DispatchCoreTest(unittest.TestCase):
    def test_dispatch_success_writes_output_and_meta(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            context_path = root / "context.md"
            output_path = root / "out.md"
            context_path.write_text("context")

            def mock_chat(**kwargs):
                self.assertEqual(kwargs["provider"], "google")
                self.assertEqual(kwargs["model"], "gemini-3-flash-preview")
                response = MagicMock()
                response.content = "hello"
                response.latency = 0.25
                response.usage = {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ), patch.dict("os.environ", {"LLM_DISPATCH_TELEMETRY_PATH": str(root / "telemetry.jsonl")}):
                result = llm_dispatch.dispatch(
                    profile="fast_extract",
                    prompt="Analyze this",
                    context_path=context_path,
                    output_path=output_path,
                )

            self.assertEqual(result.status, "ok")
            self.assertEqual(output_path.read_text(), "hello")
            meta = json.loads((root / "out.meta.json").read_text())
            self.assertEqual(meta["status"], "ok")
            self.assertEqual(meta["resolved_model"], "gemini-3-flash-preview")
            self.assertEqual(meta["usage"]["prompt_tokens"], 12)
            telemetry = [json.loads(line) for line in (root / "telemetry.jsonl").read_text().splitlines()]
            self.assertEqual(len(telemetry), 1)
            self.assertEqual(telemetry[0]["usage"]["total_tokens"], 15)

    def test_dispatch_classifies_rate_limit_and_clears_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            output_path.write_text("stale")

            def exploding_chat(**kwargs):
                raise RuntimeError("429 resource_exhausted")

            with patch.object(llm_dispatch, "_LLMX_CHAT", exploding_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="deep_review",
                    prompt="Review",
                    context_text="ctx",
                    output_path=output_path,
                )

            self.assertEqual(result.status, "rate_limit")
            self.assertFalse(output_path.exists())
            error_payload = json.loads((root / "out.error.json").read_text())
            self.assertEqual(error_payload["error_type"], "rate_limit")

    def test_dispatch_writes_parsed_json_when_schema_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            schema = {
                "type": "object",
                "properties": {"findings": {"type": "array"}},
                "required": ["findings"],
            }

            def mock_chat(**kwargs):
                self.assertIn("response_format", kwargs)
                response = MagicMock()
                response.content = '{"findings": []}'
                response.latency = 0.1
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="gpt_general",
                    prompt="Extract",
                    context_text="ctx",
                    output_path=output_path,
                    schema=schema,
                )

            self.assertEqual(result.status, "ok")
            parsed = json.loads((root / "out.parsed.json").read_text())
            self.assertEqual(parsed["findings"], [])

    def test_dispatch_carries_context_manifest_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            context_manifest = root / "context.manifest.json"
            context_manifest.write_text(
                json.dumps(
                    {
                        "payload_hash": "abc123",
                        "token_estimate": 1234,
                        "budget_metric": "tokens",
                        "estimate_method": "heuristic:chars_div_4",
                    }
                )
            )

            def mock_chat(**kwargs):
                response = MagicMock()
                response.content = "ok"
                response.latency = 0.1
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="fast_extract",
                    prompt="payload",
                    output_path=output_path,
                    context_manifest_path=context_manifest,
                )

            self.assertEqual(result.status, "ok")
            meta = json.loads((root / "out.meta.json").read_text())
            self.assertEqual(meta["context_payload_hash"], "abc123")
            self.assertEqual(meta["context_token_estimate"], 1234)
            self.assertEqual(meta["context_budget_metric"], "tokens")

    def test_dispatch_marks_parse_error_but_preserves_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            schema = {
                "type": "object",
                "properties": {"findings": {"type": "array"}},
                "required": ["findings"],
            }

            def mock_chat(**kwargs):
                response = MagicMock()
                response.content = "not json"
                response.latency = 0.1
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="fast_extract",
                    prompt="Extract",
                    context_text="ctx",
                    output_path=output_path,
                    schema=schema,
                )

            self.assertEqual(result.status, "parse_error")
            self.assertTrue(output_path.exists())
            self.assertFalse((root / "out.parsed.json").exists())
            meta = json.loads((root / "out.meta.json").read_text())
            self.assertEqual(meta["error_type"], "parse_error")

    def test_profile_input_budget_exposes_input_limits(self) -> None:
        budget = llm_dispatch.profile_input_budget("gpt_general")
        self.assertEqual(budget["profile"], "gpt_general")
        self.assertEqual(budget["input_token_limit"], 120000)
        self.assertEqual(budget["input_token_estimator"], "heuristic:chars_div_4")


if __name__ == "__main__":
    unittest.main()
