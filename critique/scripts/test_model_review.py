from __future__ import annotations

import importlib.util
import contextlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_REVIEW_PATH = SCRIPT_DIR / "model-review.py"
SPEC = importlib.util.spec_from_file_location("model_review_script", MODEL_REVIEW_PATH)
assert SPEC is not None and SPEC.loader is not None
model_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model_review)


@contextlib.contextmanager
def patched_llmx_chat(mock_chat):
    with patch.object(model_review.dispatch_core, "_LLMX_CHAT", mock_chat), patch.object(
        model_review.dispatch_core, "_LLMX_VERSION", "test"
    ):
        yield


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

    def test_dispatch_calls_both_models_and_writes_output(self) -> None:
        call_log: list[dict] = []

        def mock_chat(**kwargs):
            call_log.append(kwargs)
            resp = MagicMock()
            resp.content = f"output for {kwargs.get('model', '?')}"
            resp.latency = 1.0
            return resp

        with patched_llmx_chat(mock_chat):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal"],
                "Review this",
                has_constitution=False,
            )

        self.assertEqual(result["arch"]["exit_code"], 0)
        self.assertGreater(result["arch"]["size"], 0)
        self.assertEqual(result["formal"]["exit_code"], 0)
        self.assertGreater(result["formal"]["size"], 0)
        # Both models called
        models_called = {c["model"] for c in call_log}
        self.assertIn("gemini-3.1-pro-preview", models_called)
        self.assertIn("gpt-5.4", models_called)

    def test_dispatch_falls_back_after_gemini_rate_limit(self) -> None:
        call_count = {"arch": 0}

        def mock_chat(**kwargs):
            model = kwargs.get("model", "")
            if model == model_review.GEMINI_PRO_MODEL and call_count["arch"] == 0:
                call_count["arch"] += 1
                raise Exception("503 resource_exhausted")
            if model == model_review.GEMINI_FLASH_MODEL:
                resp = MagicMock()
                resp.content = "flash fallback"
                resp.latency = 0.5
                return resp
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 1.0
            return resp

        with patched_llmx_chat(mock_chat):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal"],
                "Review this",
                has_constitution=False,
            )

        # arch should have fallen back to Flash
        self.assertEqual(result["arch"]["model"], model_review.GEMINI_FLASH_MODEL)
        self.assertEqual(result["arch"]["fallback_reason"], "gemini_rate_limit")
        self.assertGreater(result["arch"]["size"], 0)
        # formal should succeed normally
        self.assertEqual(result["formal"]["exit_code"], 0)

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

    def test_fingerprint_merge_detects_similar_findings(self) -> None:
        """The Jaccard keyword merge should detect findings about the same issue."""
        f1 = {"title": "Missing null check in parse_config", "file": "config.py",
               "description": "parse_config does not handle None input", "confidence": 0.8,
               "category": "bug", "severity": "high", "fix": "add guard", "line": 0}
        f2 = {"title": "parse_config crashes on null input", "file": "config.py",
               "description": "Null input causes AttributeError in parse_config", "confidence": 0.7,
               "category": "bug", "severity": "high", "fix": "validate input", "line": 0}
        # Simulate what extract_claims merge does
        import re
        def _fp(f):
            text = f"{f.get('title', '')} {f.get('file', '')} {f.get('description', '')[:200]}"
            words = set(re.findall(r"[a-z_]{4,}", text.lower()))
            words -= {"this", "that", "with", "from", "should", "could", "would", "does", "have", "will", "also", "been"}
            return words

        fp1, fp2 = _fp(f1), _fp(f2)
        jaccard = len(fp1 & fp2) / len(fp1 | fp2)
        self.assertGreater(jaccard, 0.3, f"Expected Jaccard > 0.3, got {jaccard:.2f}")


class SchemaTransformTest(unittest.TestCase):
    def test_add_additional_properties_to_nested_objects(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"name": {"type": "string"}}},
                }
            },
        }
        result = model_review._add_additional_properties(schema)
        self.assertFalse(result["additionalProperties"])
        self.assertFalse(result["properties"]["items"]["items"]["additionalProperties"])
        # Original not mutated
        self.assertNotIn("additionalProperties", schema)

    def test_strip_additional_properties_from_nested_objects(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": False, "properties": {}},
                }
            },
        }
        result = model_review._strip_additional_properties(schema)
        self.assertNotIn("additionalProperties", result)
        self.assertNotIn("additionalProperties", result["properties"]["items"]["items"])
        # Original not mutated
        self.assertIn("additionalProperties", schema)

    def test_finding_schema_roundtrips_both_providers(self) -> None:
        """The canonical FINDING_SCHEMA should be valid after both transforms."""
        oai = model_review._add_additional_properties(model_review.FINDING_SCHEMA)
        self.assertFalse(oai["additionalProperties"])
        self.assertFalse(oai["properties"]["findings"]["items"]["additionalProperties"])

        google = model_review._strip_additional_properties(model_review.FINDING_SCHEMA)
        self.assertNotIn("additionalProperties", google)


class CallLlmxTest(unittest.TestCase):
    def test_call_llmx_returns_error_dict_on_exception(self) -> None:
        def exploding_chat(**kwargs):
            raise ConnectionError("network down")

        with tempfile.TemporaryDirectory() as td:
            ctx = Path(td) / "ctx.md"
            ctx.write_text("context")
            out = Path(td) / "out.md"
            with patched_llmx_chat(exploding_chat):
                result = model_review._call_llmx(
                    provider="google", model="gemini-3.1-pro-preview",
                    context_path=ctx, prompt="test", output_path=out,
                    timeout=10,
                )
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["size"], 0)
        self.assertIn("network down", result["error"])

    def test_call_llmx_passes_schema_for_openai(self) -> None:
        captured = {}
        def capture_chat(**kwargs):
            captured.update(kwargs)
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 0.1
            return resp

        with tempfile.TemporaryDirectory() as td:
            ctx = Path(td) / "ctx.md"
            ctx.write_text("context")
            out = Path(td) / "out.md"
            with patched_llmx_chat(capture_chat):
                model_review._call_llmx(
                    provider="openai", model="gpt-5.4",
                    context_path=ctx, prompt="test", output_path=out,
                    schema=model_review.FINDING_SCHEMA, timeout=10,
                )
        # Should have additionalProperties added for OpenAI
        fmt = captured.get("response_format", {})
        self.assertIn("additionalProperties", str(fmt))

    def test_call_llmx_strips_schema_for_google(self) -> None:
        captured = {}
        def capture_chat(**kwargs):
            captured.update(kwargs)
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 0.1
            return resp

        with tempfile.TemporaryDirectory() as td:
            ctx = Path(td) / "ctx.md"
            ctx.write_text("context")
            out = Path(td) / "out.md"
            with patched_llmx_chat(capture_chat):
                model_review._call_llmx(
                    provider="google", model="gemini-3.1-pro-preview",
                    context_path=ctx, prompt="test", output_path=out,
                    schema={"type": "object", "additionalProperties": False, "properties": {}},
                    timeout=10,
                )
        fmt = captured.get("response_format", {})
        self.assertNotIn("additionalProperties", str(fmt))


class AxisResolutionTest(unittest.TestCase):
    def test_standard_preset_is_gpt_inclusive(self) -> None:
        self.assertEqual(model_review.resolve_axes("standard"), ["arch", "formal"])

    def test_simple_preset_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "simple"):
            model_review.resolve_axes("simple")

    def test_non_gpt_axis_sets_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "GPT-backed axis"):
            model_review.resolve_axes("arch,domain,mechanical")

    def test_internal_non_gpt_axis_sets_can_opt_in(self) -> None:
        self.assertEqual(
            model_review.resolve_axes("arch,domain,mechanical", allow_non_gpt=True),
            ["arch", "domain", "mechanical"],
        )


class UnderspecifiedPromptTest(unittest.TestCase):
    def test_bare_close_is_rewritten(self) -> None:
        out = model_review._rewrite_underspecified_prompt("close", "plan-X")
        self.assertIn("Adversarial review of: plan-X", out)
        self.assertIn("touched file", out)

    def test_empty_is_rewritten(self) -> None:
        out = model_review._rewrite_underspecified_prompt("", "topic")
        self.assertIn("Adversarial review", out)

    def test_single_verb_is_rewritten(self) -> None:
        for verb in ("review", "verify", "check", "full", "audit"):
            out = model_review._rewrite_underspecified_prompt(verb, "t")
            self.assertIn("Adversarial review", out, msg=f"verb={verb}")

    def test_real_question_passes_through(self) -> None:
        q = "Find bugs in the signal-merging logic introduced by commit abc123."
        self.assertEqual(model_review._rewrite_underspecified_prompt(q, "topic"), q)

    def test_multi_word_short_question_passes_through(self) -> None:
        q = "Review the PRS flow for edge cases."
        self.assertEqual(model_review._rewrite_underspecified_prompt(q, "topic"), q)


class ExtractionCoverageTest(unittest.TestCase):
    def test_extract_claims_writes_coverage_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            review_dir = Path(td)
            arch_output = review_dir / "arch-output.md"
            arch_output.write_text("arch output")
            formal_output = review_dir / "formal-output.md"
            formal_output.write_text("formal output")
            (review_dir / "shared-context.md").write_text("# shared context")
            (review_dir / "shared-context.manifest.json").write_text(
                json.dumps(
                    {
                        "builder_name": "model_review_context",
                        "builder_version": "2026-04-10-v1",
                        "payload_hash": "payload-hash",
                        "rendered_content_hash": "content-hash",
                        "rendered_bytes": 120,
                        "token_estimate": 30,
                        "estimate_method": "heuristic:chars_div_4",
                        "budget_metric": "tokens",
                        "budget_limit": 42,
                        "source_paths": ["context.md"],
                        "truncation_events": [],
                        "packet_metadata": {
                            "budget_enforcement": {
                                "dropped_blocks": [{"block_title": "context.md"}],
                            }
                        },
                    }
                )
            )

            dispatch_result = {
                "review_dir": str(review_dir),
                "axes": ["arch", "formal"],
                "queries": 2,
                "elapsed_seconds": 1.0,
                "arch": {
                    "label": "Gemini (architecture/patterns)",
                    "model": "gemini-3.1-pro-preview",
                    "requested_model": "gemini-3.1-pro-preview",
                    "exit_code": 0,
                    "size": 12,
                    "output": str(arch_output),
                },
                "formal": {
                    "label": "GPT-5.4 (quantitative/formal)",
                    "model": "gpt-5.4",
                    "requested_model": "gpt-5.4",
                    "exit_code": 0,
                    "size": 12,
                    "output": str(formal_output),
                },
            }

            def mock_call_llmx(**kwargs):
                output_path = Path(kwargs["output_path"])
                if output_path.name == "arch-extraction.json":
                    payload = {
                        "findings": [
                            {
                                "category": "bug",
                                "severity": "high",
                                "title": "Missing guard",
                                "description": "arch bug",
                                "file": "review.py",
                                "line": 12,
                                "fix": "add guard",
                                "confidence": 0.9,
                            }
                        ]
                    }
                else:
                    payload = {
                        "findings": [
                            {
                                "category": "logic",
                                "severity": "medium",
                                "title": "Cost mismatch",
                                "description": "formal bug",
                                "file": "model.py",
                                "line": 8,
                                "fix": "adjust formula",
                                "confidence": 0.8,
                            }
                        ]
                    }
                output_path.write_text(json.dumps(payload))
                return {"exit_code": 0, "size": output_path.stat().st_size, "latency": 0.1, "error": None}

            with patch.object(model_review, "_call_llmx", side_effect=mock_call_llmx):
                disposition_path = model_review.extract_claims(review_dir, dispatch_result)

            self.assertEqual(Path(disposition_path).name, "disposition.md")
            coverage_path = review_dir / "coverage.json"
            self.assertTrue(coverage_path.exists())
            coverage = json.loads(coverage_path.read_text())
            self.assertEqual(coverage["schema"], "review-coverage.v1")
            self.assertEqual(coverage["schema_version"], "review-coverage.v1")
            self.assertEqual(coverage["dispatch"]["requested_axis_count"], 2)
            self.assertEqual(coverage["dispatch"]["axes"][1]["model"], "gpt-5.4")
            self.assertEqual(coverage["context_packet"]["payload_hash"], "payload-hash")
            self.assertEqual(coverage["context_packet"]["dropped_blocks"][0]["block_title"], "context.md")
            self.assertEqual(coverage["extraction"]["usable_axis_count"], 2)
            self.assertEqual(coverage["extraction"]["axes_with_findings_count"], 2)
            self.assertEqual(coverage["extraction"]["findings_before_dedup"], 2)
            self.assertEqual(coverage["extraction"]["findings_after_dedup"], 2)
            self.assertEqual(coverage["extraction"]["findings_by_axis"]["arch"], 1)
            self.assertEqual(coverage["extraction"]["findings_by_axis"]["formal"], 1)
            self.assertEqual(coverage["extraction"]["coverage_ratio"], 1.0)
            self.assertEqual(Path(coverage["artifacts"]["disposition"]).name, "disposition.md")
            self.assertFalse(coverage["verification"]["enabled"])

    def test_verify_claims_updates_coverage_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            review_dir = Path(td)
            project_dir = review_dir / "project"
            project_dir.mkdir()
            source_file = project_dir / "module.py"
            source_file.write_text("value = 1\n")
            disposition = review_dir / "disposition.md"
            disposition.write_text(
                "# Review Findings\n\n"
                "1. `module.py:1` defines `value` with the wrong value\n"
                "2. `missing.py:1` is referenced but absent\n"
            )
            coverage = {
                "schema_version": "review-coverage.v1",
                "review_dir": str(review_dir),
                "artifacts": {"disposition": str(disposition)},
                "context_packet": {},
                "dispatch": {},
                "extraction": {"enabled": True},
                "verification": {"enabled": False},
            }
            (review_dir / "coverage.json").write_text(json.dumps(coverage))

            verified_path = model_review.verify_claims(review_dir, str(disposition), project_dir)

            self.assertEqual(Path(verified_path).name, "verified-disposition.md")
            updated = json.loads((review_dir / "coverage.json").read_text())
            self.assertTrue(updated["verification"]["enabled"])
            self.assertEqual(updated["verification"]["claim_count"], 2)
            self.assertEqual(updated["verification"]["confirmed_count"], 1)
            self.assertEqual(updated["verification"]["corrected_count"], 0)
            self.assertEqual(updated["verification"]["hallucinated_count"], 1)
            self.assertEqual(updated["verification"]["inconclusive_count"], 0)
            self.assertEqual(updated["verification"]["unverifiable_count"], 0)
            self.assertEqual(updated["verification"]["hallucination_rate"], 0.5)
            self.assertEqual(Path(updated["artifacts"]["verified_disposition"]).name, "verified-disposition.md")

    def test_verify_claims_parses_multiline_disposition_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            review_dir = Path(td)
            project_dir = review_dir / "project"
            (project_dir / "review" / "scripts").mkdir(parents=True)
            source_file = project_dir / "review" / "scripts" / "model-review.py"
            source_file.write_text("def verify_claims():\n    return 0\n")
            disposition = review_dir / "disposition.md"
            disposition.write_text(
                "# Review Findings\n\n"
                "1. **[HIGH]** verify_claims misses multiline file refs\n"
                "   Category: logic | Confidence: 0.9 | Source: formal\n"
                "   The verifier ignores file references on metadata lines.\n"
                "   File: review/scripts/model-review.py:1\n"
                "   Fix: parse full finding blocks\n\n"
                "---\n\n"
                "## Agent Response (fill before implementing)\n"
            )
            coverage = {
                "schema_version": "review-coverage.v1",
                "review_dir": str(review_dir),
                "artifacts": {"disposition": str(disposition)},
                "context_packet": {},
                "dispatch": {},
                "extraction": {"enabled": True},
                "verification": {"enabled": False},
            }
            (review_dir / "coverage.json").write_text(json.dumps(coverage))

            verified_path = model_review.verify_claims(review_dir, str(disposition), project_dir)

            self.assertEqual(Path(verified_path).name, "verified-disposition.md")
            verified_text = Path(verified_path).read_text()
            self.assertIn("| 1 | CONFIRMED |", verified_text)

    def test_verify_claims_prefers_structured_findings_and_can_correct_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            review_dir = Path(td)
            project_dir = review_dir / "project"
            (project_dir / "review" / "scripts").mkdir(parents=True)
            source_file = project_dir / "review" / "scripts" / "model-review.py"
            source_file.write_text("def verify_claims():\n    return 0\n")
            disposition = review_dir / "disposition.md"
            disposition.write_text("# Review Findings\n\n1. Placeholder finding\n")
            findings = {
                "findings": [
                    {
                        "id": 1,
                        "title": "verify_claims() line reference is stale",
                        "description": "The finding points at verify_claims() in review/scripts/model-review.py",
                        "file": "review/scripts/model-review.py",
                        "line": 99,
                        "fix": "update the stale line reference",
                        "category": "logic",
                        "severity": "medium",
                        "confidence": 0.8,
                    }
                ]
            }
            (review_dir / "findings.json").write_text(json.dumps(findings))
            coverage = {
                "schema_version": "review-coverage.v1",
                "review_dir": str(review_dir),
                "artifacts": {"disposition": str(disposition)},
                "context_packet": {},
                "dispatch": {},
                "extraction": {"enabled": True},
                "verification": {"enabled": False},
            }
            (review_dir / "coverage.json").write_text(json.dumps(coverage))

            verified_path = model_review.verify_claims(review_dir, str(disposition), project_dir)

            updated = json.loads((review_dir / "coverage.json").read_text())
            self.assertEqual(updated["verification"]["claim_count"], 1)
            self.assertEqual(updated["verification"]["corrected_count"], 1)
            self.assertEqual(updated["verification"]["confirmed_count"], 0)
            verified_text = Path(verified_path).read_text()
            self.assertIn("| 1 | CORRECTED |", verified_text)


class ModelReviewMainTest(unittest.TestCase):
    def test_main_accepts_explicit_extract_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            review_dir = project_dir / ".model-review" / "auto"
            review_dir.mkdir(parents=True)
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
                    "size": 10,
                    "output": str(review_dir / "formal-output.md"),
                },
            }
            (review_dir / "formal-output.md").write_text("output")
            coverage_path = review_dir / "coverage.json"
            coverage_path.write_text(json.dumps({"schema": "review-coverage.v1", "schema_version": 1}))

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review, "build_context", return_value={"formal": project_dir / "ctx.md"}), \
                     patch.object(model_review, "dispatch", return_value=dispatch_result), \
                     patch.object(model_review, "find_constitution", return_value=("", None)), \
                     patch.object(model_review, "extract_claims", return_value=str(review_dir / "disposition.md")) as mock_extract, \
                     patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x13"), \
                     patch.object(model_review.sys, "argv", [
                         "model-review.py",
                         "--context", str(context_path),
                         "--topic", "explicit-extract",
                         "--project", str(project_dir),
                         "--extract",
                     ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 0)
            mock_extract.assert_called_once()

    def test_main_extracts_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            review_dir = project_dir / ".model-review" / "auto"
            review_dir.mkdir(parents=True)
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
                    "size": 10,
                    "output": str(review_dir / "formal-output.md"),
                },
            }
            (review_dir / "formal-output.md").write_text("output")
            coverage_path = review_dir / "coverage.json"
            coverage_path.write_text(json.dumps({"schema": "review-coverage.v1", "schema_version": 1}))

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review, "build_context", return_value={"formal": project_dir / "ctx.md"}), \
                     patch.object(model_review, "dispatch", return_value=dispatch_result), \
                     patch.object(model_review, "find_constitution", return_value=("", None)), \
                     patch.object(model_review, "extract_claims", return_value=str(review_dir / "disposition.md")) as mock_extract, \
                     patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x12"), \
                     patch.object(model_review.sys, "argv", [
                         "model-review.py",
                         "--context", str(context_path),
                         "--topic", "default-extract",
                         "--project", str(project_dir),
                     ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 0)
            mock_extract.assert_called_once()

    def test_main_returns_nonzero_when_axis_output_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")

            dispatch_result = {
                "review_dir": str(project_dir / ".model-review" / "test"),
                "axes": ["formal"],
                "queries": 1,
                "elapsed_seconds": 1.0,
                "formal": {
                    "label": "Formal",
                    "model": "gpt-5.4",
                    "requested_model": "gpt-5.4",
                    "exit_code": 0,
                    "size": 0,
                    "output": str(project_dir / "formal-output.md"),
                    "stderr": "0-byte output",
                },
            }

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review, "build_context", return_value={"formal": project_dir / "ctx.md"}), \
                     patch.object(model_review, "dispatch", return_value=dispatch_result), \
                     patch.object(model_review, "find_constitution", return_value=("", None)), \
                     patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x12"), \
                     patch.object(model_review.sys, "argv", [
                         "model-review.py", "--context", str(context_path),
                         "--topic", "empty-axis", "--project", str(project_dir),
                     ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 2)

    def test_main_rejects_verify_with_no_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "invalid",
                    "--project", str(project_dir),
                    "--verify",
                    "--no-extract",
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)

    def test_main_rejects_non_gpt_axes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "non-gpt",
                    "--project", str(project_dir),
                    "--axes", "arch,domain,mechanical",
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)

    def test_main_rejects_invalid_questions_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            questions_path = project_dir / "questions.json"
            questions_path.write_text('{"arch": ')

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "bad-questions",
                    "--project", str(project_dir),
                    "--questions", str(questions_path),
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)


class ModelReviewContextBuildTest(unittest.TestCase):
    def test_build_context_drops_file_specs_when_budget_is_tiny(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            context_file = project_dir / "context.txt"
            context_file.write_text("A" * 4000)

            ctx_files = model_review.build_context(
                review_dir,
                project_dir,
                context_file=None,
                axis_names=["formal"],
                context_file_specs=[str(context_file)],
                budget_limit_override=120,
            )

            shared_ctx = ctx_files["formal"]
            manifest = json.loads(shared_ctx.manifest_path.read_text())
            dropped = manifest["packet_metadata"]["budget_enforcement"]["dropped_blocks"]
            self.assertTrue(dropped)
            self.assertEqual(dropped[0]["block_title"], str(context_file))

    def test_build_context_keeps_explicit_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            context_file = project_dir / "assembled.md"
            context_file.write_text("B" * 4000)

            ctx_files = model_review.build_context(
                review_dir,
                project_dir,
                context_file=context_file,
                axis_names=["formal"],
                budget_limit_override=120,
            )

            shared_ctx = ctx_files["formal"]
            manifest = json.loads(shared_ctx.manifest_path.read_text())
            dropped = manifest["packet_metadata"]["budget_enforcement"]["dropped_blocks"]
            self.assertEqual(dropped, [])
            self.assertIn(str(context_file), shared_ctx.content_path.read_text())


if __name__ == "__main__":
    unittest.main()
