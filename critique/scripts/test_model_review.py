from __future__ import annotations

import importlib.util
import contextlib
import json
import os
import tempfile
import time
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
    with (
        patch.object(model_review.dispatch_core, "_LLMX_CHAT", mock_chat),
        patch.object(model_review.dispatch_core, "_LLMX_VERSION", "test"),
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
                has_governance=False,
            )

        self.assertEqual(result["arch"]["exit_code"], 0)
        self.assertGreater(result["arch"]["size"], 0)
        self.assertEqual(result["formal"]["exit_code"], 0)
        self.assertGreater(result["formal"]["size"], 0)
        # Both models called
        models_called = {c["model"] for c in call_log}
        self.assertIn("gemini-3.5-flash", models_called)
        self.assertTrue(any("gpt-5.6" in m for m in models_called), models_called)

    def test_dispatch_falls_back_after_gemini_rate_limit(self) -> None:
        call_count = {"arch": 0}

        def mock_chat(**kwargs):
            model = kwargs.get("model", "")
            if model == model_review.GEMINI_PRIMARY_MODEL and call_count["arch"] == 0:
                call_count["arch"] += 1
                raise Exception("503 resource_exhausted")
            if model == model_review.GEMINI_FALLBACK_MODEL:
                resp = MagicMock()
                resp.content = "fallback output"
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
                has_governance=False,
            )

        # arch should have fallen back to the runner-up critique model (3.1-Pro)
        self.assertEqual(result["arch"]["model"], model_review.GEMINI_FALLBACK_MODEL)
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
                "model": "gpt-5.6-luna",
                "requested_model": "gpt-5.6-luna",
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
        f1 = {
            "title": "Missing null check in parse_config",
            "file": "config.py",
            "description": "parse_config does not handle None input",
            "confidence": 0.8,
            "category": "bug",
            "severity": "high",
            "fix": "add guard",
            "line": 0,
        }
        f2 = {
            "title": "parse_config crashes on null input",
            "file": "config.py",
            "description": "Null input causes AttributeError in parse_config",
            "confidence": 0.7,
            "category": "bug",
            "severity": "high",
            "fix": "validate input",
            "line": 0,
        }
        # Simulate what extract_claims merge does
        import re

        def _fp(f):
            text = f"{f.get('title', '')} {f.get('file', '')} {f.get('description', '')[:200]}"
            words = set(re.findall(r"[a-z_]{4,}", text.lower()))
            words -= {
                "this",
                "that",
                "with",
                "from",
                "should",
                "could",
                "would",
                "does",
                "have",
                "will",
                "also",
                "been",
            }
            return words

        fp1, fp2 = _fp(f1), _fp(f2)
        jaccard = len(fp1 & fp2) / len(fp1 | fp2)
        threshold = model_review.CROSS_MODEL_JACCARD_THRESHOLD
        self.assertGreater(
            jaccard,
            threshold,
            f"Expected Jaccard > {threshold} (production merge threshold), got {jaccard:.2f}",
        )


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
                    provider="google",
                    model="gemini-3.5-flash",
                    context_path=ctx,
                    prompt="test",
                    output_path=out,
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
                    provider="openai",
                    model="gpt-5.6-luna",
                    context_path=ctx,
                    prompt="test",
                    output_path=out,
                    schema=model_review.FINDING_SCHEMA,
                    timeout=10,
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
                    provider="google",
                    model="gemini-3.5-flash",
                    context_path=ctx,
                    prompt="test",
                    output_path=out,
                    schema={"type": "object", "additionalProperties": False, "properties": {}},
                    timeout=10,
                )
        fmt = captured.get("response_format", {})
        self.assertNotIn("additionalProperties", str(fmt))

    def test_call_llmx_honors_cli_transport_for_composer(self) -> None:
        """CLI-transport profiles must keep auth=subscription from the profile."""
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
                    provider="cursor",
                    model="composer-2.5",
                    context_path=ctx,
                    prompt="test",
                    output_path=out,
                    timeout=10,
                )
        self.assertEqual(captured.get("provider"), "cursor")
        self.assertEqual(
            captured.get("auth"), "subscription", "composer must use profile auth=subscription"
        )
        self.assertEqual(captured.get("mode"), "chat")

    def test_call_llmx_keeps_api_auth_for_api_profiles(self) -> None:
        """API-backed profiles keep auth=api (skip CLI fallback latency)."""
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
                    provider="openai",
                    model="gpt-5.6-luna",
                    context_path=ctx,
                    prompt="test",
                    output_path=out,
                    timeout=10,
                )
        self.assertEqual(captured.get("auth"), "api", "API profiles must keep auth=api")
        self.assertEqual(captured.get("mode"), "chat")

    def test_call_llmx_honors_cli_transport_for_claude(self) -> None:
        """claude_review must route via auth=subscription, not metered API."""
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
                    provider="anthropic",
                    model="claude-opus-4-8",
                    context_path=ctx,
                    prompt="test",
                    output_path=out,
                    timeout=10,
                )
        self.assertEqual(captured.get("provider"), "anthropic")
        self.assertEqual(
            captured.get("auth"), "subscription", "claude must use profile auth=subscription"
        )
        self.assertEqual(captured.get("mode"), "chat")


class AxisResolutionTest(unittest.TestCase):
    def test_standard_preset_is_gpt_inclusive(self) -> None:
        axes = model_review.resolve_axes("standard")
        self.assertEqual(axes, ["arch", "gaps", "correctness", "contracts"])
        self.assertTrue(any(model_review.axis_uses_gpt(a) for a in axes))

    def test_preset_plus_axis_expansion(self) -> None:
        axes = model_review.resolve_axes("standard,formal")
        self.assertEqual(
            axes,
            ["arch", "gaps", "correctness", "contracts", "formal"],
        )
        self.assertEqual(
            model_review.resolve_axes("cross2,formal"), ["arch", "correctness", "formal"]
        )

    def test_cross2_preset_diagonal(self) -> None:
        axes = model_review.resolve_axes("cross2")
        self.assertEqual(axes, ["arch", "correctness"])
        self.assertEqual(model_review.AXIS_CELLS["arch"]["cell"], "S_G")
        self.assertEqual(model_review.AXIS_CELLS["correctness"]["cell"], "M_P")

    def test_cross4_matches_standard_geometry(self) -> None:
        self.assertEqual(
            model_review.resolve_axes("cross4"),
            model_review.resolve_axes("standard"),
        )

    def test_lens2_alias_cross2(self) -> None:
        self.assertEqual(
            model_review.resolve_axes("lens2"),
            model_review.resolve_axes("cross2"),
        )

    def test_simple_preset_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "simple"):
            model_review.resolve_axes("simple")

    def test_non_gpt_axis_sets_are_rejected(self) -> None:
        # arch/domain/alternatives are the Gemini-backed axes (mechanical is now
        # GPT-backed, gpt-5.6-luna @ low effort).
        with self.assertRaisesRegex(ValueError, "--allow-non-gpt"):
            model_review.resolve_axes("arch,domain,alternatives")

    def test_internal_non_gpt_axis_sets_can_opt_in(self) -> None:
        self.assertEqual(
            model_review.resolve_axes("arch,domain,alternatives", allow_non_gpt=True),
            ["arch", "domain", "alternatives"],
        )

    def test_grok_axis_resolves_to_exact_repo_workspace_profile(self) -> None:
        axes = model_review.resolve_axes("standard,grok")
        self.assertIn("grok", axes)
        self.assertTrue(model_review.axis_needs_repo_workspace("grok"))
        self.assertFalse(model_review.axis_needs_repo_workspace("composer"))
        self.assertEqual(model_review.AXES["grok"]["profile"], "grok_review")
        profile = model_review.dispatch_core.PROFILES["grok_review"]
        self.assertEqual(profile.model, "cursor-grok-4.5-high")
        self.assertEqual(profile.provider, "cursor")
        self.assertEqual(model_review._resolved_axis_timeout("grok"), 1200)
        self.assertGreater(
            model_review._parallel_dispatch_wait_default(["grok"]),
            model_review._resolved_axis_timeout("grok"),
        )

    def test_claude_axis_has_long_review_timeout_and_executor_headroom(self) -> None:
        from shared.llm_dispatch import PROFILES

        self.assertEqual(model_review._resolved_axis_timeout("claude"), 3600)
        self.assertEqual(PROFILES["claude_review"].reasoning_effort, "max")
        self.assertGreater(
            model_review._parallel_dispatch_wait_default(["grok", "claude"]),
            model_review._resolved_axis_timeout("claude"),
        )

    def test_call_cursor_repo_agent_uses_exact_read_only_workspace_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "context.md"
            context_path.write_text("# packet\nclaim: foo exists\n")
            output_path = root / "grok-output.md"
            completed = model_review.subprocess.CompletedProcess(
                [], 0, stdout="## Premises checked\nOK\n", stderr=""
            )
            with (
                patch.object(
                    model_review,
                    "_resolve_cursor_agent_bin",
                    return_value="/usr/bin/cursor-agent",
                ),
                patch.object(
                    model_review, "_run_cursor_command", return_value=completed
                ) as run,
            ):
                result = model_review._call_cursor_repo_agent(
                    model="cursor-grok-4.5-high",
                    project_dir=root,
                    context_path=context_path,
                    prompt="Review this.",
                    output_path=output_path,
                    timeout=30,
                )

            self.assertEqual(result["exit_code"], 0)
            command = run.call_args.args[0]
            self.assertIn("--mode", command)
            self.assertEqual(command[command.index("--mode") + 1], "ask")
            self.assertEqual(
                command[command.index("--model") + 1], "cursor-grok-4.5-high"
            )
            self.assertEqual(
                command[command.index("--workspace") + 1], str(root.resolve())
            )
            self.assertEqual(run.call_args.kwargs["cwd"], root)
            self.assertIn("OK", output_path.read_text())

    def test_call_cursor_repo_agent_refuses_retired_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "context.md"
            context_path.write_text("packet")
            result = model_review._call_cursor_repo_agent(
                model="grok-4.5-xhigh",
                project_dir=root,
                context_path=context_path,
                prompt="Review this.",
                output_path=root / "output.md",
                timeout=30,
            )
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("non-canonical", result["error"])

    def test_cursor_runner_uses_isolated_popen_not_subprocess_run(self) -> None:
        process = MagicMock()
        process.returncode = 0
        process.communicate.return_value = ("OK\n", "")
        with patch.object(model_review.subprocess, "Popen", return_value=process) as popen:
            completed = model_review._run_cursor_command(
                ["/usr/bin/cursor-agent", "models"],
                input_text="probe",
                timeout=30,
                cwd=Path("/tmp/workspace"),
            )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "OK\n")
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertEqual(popen.call_args.kwargs["cwd"], "/tmp/workspace")
        process.communicate.assert_called_once_with(input="probe", timeout=30)

    def test_dispatch_grok_requires_project_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            context_path = root / "context.md"
            context_path.write_text("packet")
            result = model_review.dispatch(
                review_dir,
                {"grok": context_path},
                ["grok"],
                "Review this",
                False,
                project_dir=None,
            )
        self.assertEqual(result["grok"]["exit_code"], 1)
        self.assertEqual(
            result["grok"]["failure_reason"], "repo_workspace_requires_project_dir"
        )


class StructuralAssumptionsTest(unittest.TestCase):
    def test_parse_structural_assumptions_bullets(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "arch-output.md"
            p.write_text(
                "### Structural assumptions:\n"
                "- Callers exist for every gateway entrypoint\n"
                "- Join keys match on both sides of the outbox\n"
                "\n## 9. Other\n"
            )
            got = model_review.parse_structural_assumptions(p)
            self.assertEqual(len(got), 2)
            self.assertIn("Callers exist", got[0])

    def test_collect_assumptions_empty_without_section(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td)
            (rd / "arch-output.md").write_text("## 1. No assumptions section\n")
            self.assertEqual(model_review.collect_structural_assumptions(rd, ["arch"]), [])

    def test_format_cross_talk_injection(self) -> None:
        inj = model_review.format_cross_talk_injection(["premise A", "premise B"])
        self.assertIn("premise A", inj)
        self.assertIn("STRUCTURAL ASSUMPTIONS", inj)

    def test_split_axes_by_lens(self) -> None:
        s, m, o = model_review.split_axes_by_lens(["arch", "correctness", "formal"])
        self.assertEqual(s, ["arch"])
        self.assertEqual(m, ["correctness"])
        self.assertEqual(o, ["formal"])


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
                    "model": "gemini-3.5-flash",
                    "requested_model": "gemini-3.5-flash",
                    "exit_code": 0,
                    "size": 12,
                    "output": str(arch_output),
                },
                "formal": {
                    "label": "GPT-5.5 (quantitative/formal)",
                    "model": "gpt-5.6-luna",
                    "requested_model": "gpt-5.6-luna",
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
                return {
                    "exit_code": 0,
                    "size": output_path.stat().st_size,
                    "latency": 0.1,
                    "error": None,
                }

            with patch.object(model_review, "_call_llmx", side_effect=mock_call_llmx):
                disposition_path = model_review.extract_claims(review_dir, dispatch_result)

            self.assertEqual(Path(disposition_path).name, "disposition.md")
            coverage_path = review_dir / "coverage.json"
            self.assertTrue(coverage_path.exists())
            coverage = json.loads(coverage_path.read_text())
            self.assertEqual(coverage["schema"], "review-coverage.v1")
            self.assertEqual(coverage["schema_version"], "review-coverage.v1")
            self.assertEqual(coverage["dispatch"]["requested_axis_count"], 2)
            self.assertIn("gpt-5.6", coverage["dispatch"]["axes"][1]["model"])
            self.assertEqual(coverage["context_packet"]["payload_hash"], "payload-hash")
            self.assertEqual(
                coverage["context_packet"]["dropped_blocks"][0]["block_title"], "context.md"
            )
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
            self.assertEqual(
                Path(updated["artifacts"]["verified_disposition"]).name, "verified-disposition.md"
            )

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
    def setUp(self) -> None:
        self._premise_scout_guard = patch.object(
            model_review,
            "run_premise_scout",
            side_effect=AssertionError(
                "ModelReviewMainTest must never launch a live premise scout"
            ),
        )
        self.mock_run_premise_scout = self._premise_scout_guard.start()
        self.addCleanup(self._premise_scout_guard.stop)

    def test_cli_uses_named_question_and_repeatable_context_files(self) -> None:
        with (
            patch.object(model_review, "run_preflight", return_value=0) as mock_preflight,
            patch.object(
                model_review.sys,
                "argv",
                [
                    "model-review.py",
                    "--preflight",
                    "--context-file",
                    "plan.md",
                    "--context-file",
                    "scripts/worker.py:10-20",
                    "--question",
                    "Review the worker boundary",
                ],
            ),
        ):
            self.assertEqual(model_review.main(), 0)
            mock_preflight.assert_called_once_with(
                Path.cwd().resolve(), include_grok=False
            )

    def test_cli_preflight_opts_into_grok_for_requested_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            with (
                patch.object(model_review, "run_preflight", return_value=0) as preflight,
                patch.object(
                    model_review.sys,
                    "argv",
                    [
                        "model-review.py",
                        "--preflight",
                        "--axes",
                        "grok",
                        "--project",
                        str(project_dir),
                    ],
                ),
            ):
                self.assertEqual(model_review.main(), 0)
            preflight.assert_called_once_with(
                project_dir.resolve(), include_grok=True
            )

    def test_cli_rejects_removed_greedy_context_files_flag(self) -> None:
        with (
            patch.object(
                model_review.sys,
                "argv",
                [
                    "model-review.py",
                    "--preflight",
                    "--context-files",
                    "plan.md",
                    "Review text that must not become a path",
                ],
            ),
            self.assertRaises(SystemExit) as raised,
        ):
            model_review.main()
        self.assertEqual(raised.exception.code, 2)

    def test_grok_preflight_failure_blocks_before_review_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("# review packet\n")
            with (
                patch.object(
                    model_review.sys,
                    "argv",
                    [
                        "model-review.py",
                        "--project",
                        str(project_dir),
                        "--context",
                        str(context_path),
                        "--axes",
                        "standard,grok",
                    ],
                ),
                patch.object(
                    model_review,
                    "run_grok_preflight",
                    return_value=(1, {"ok": False, "registry": {"ok": False}}),
                ),
                patch.object(model_review, "create_review_dir") as create_review_dir,
            ):
                self.assertEqual(model_review.main(), 1)
            create_review_dir.assert_not_called()

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
                    "model": "gpt-5.6-luna",
                    "requested_model": "gpt-5.6-luna",
                    "exit_code": 0,
                    "size": 10,
                    "output": str(review_dir / "formal-output.md"),
                },
            }
            (review_dir / "formal-output.md").write_text("output")
            coverage_path = review_dir / "coverage.json"
            coverage_path.write_text(
                json.dumps({"schema": "review-coverage.v1", "schema_version": 1})
            )

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with (
                    patch.object(
                        model_review,
                        "build_context",
                        return_value={"formal": project_dir / "ctx.md"},
                    ),
                    patch.object(model_review, "dispatch", return_value=dispatch_result),
                    patch.object(model_review, "find_governance", return_value=None),
                    patch.object(
                        model_review,
                        "extract_claims",
                        return_value=str(review_dir / "disposition.md"),
                    ) as mock_extract,
                    patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x13"),
                    patch.object(
                        model_review.sys,
                        "argv",
                        [
                            "model-review.py",
                            "--context",
                            str(context_path),
                            "--topic",
                            "explicit-extract",
                            "--project",
                            str(project_dir),
                            "--axes",
                            "formal",
                            "--no-scout",
                            "--extract",
                        ],
                    ),
                ):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 0)
            mock_extract.assert_called_once()
            self.mock_run_premise_scout.assert_not_called()

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
                    "model": "gpt-5.6-luna",
                    "requested_model": "gpt-5.6-luna",
                    "exit_code": 0,
                    "size": 10,
                    "output": str(review_dir / "formal-output.md"),
                },
            }
            (review_dir / "formal-output.md").write_text("output")
            coverage_path = review_dir / "coverage.json"
            coverage_path.write_text(
                json.dumps({"schema": "review-coverage.v1", "schema_version": 1})
            )

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with (
                    patch.object(
                        model_review,
                        "build_context",
                        return_value={"formal": project_dir / "ctx.md"},
                    ),
                    patch.object(model_review, "dispatch", return_value=dispatch_result),
                    patch.object(model_review, "find_governance", return_value=None),
                    patch.object(
                        model_review,
                        "extract_claims",
                        return_value=str(review_dir / "disposition.md"),
                    ) as mock_extract,
                    patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x12"),
                    patch.object(
                        model_review.sys,
                        "argv",
                        [
                            "model-review.py",
                            "--context",
                            str(context_path),
                            "--topic",
                            "default-extract",
                            "--project",
                            str(project_dir),
                            "--axes",
                            "formal",
                            "--no-scout",
                        ],
                    ),
                ):
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
                    "model": "gpt-5.6-luna",
                    "requested_model": "gpt-5.6-luna",
                    "exit_code": 0,
                    "size": 0,
                    "output": str(project_dir / "formal-output.md"),
                    "stderr": "0-byte output",
                },
            }

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with (
                    patch.object(
                        model_review,
                        "build_context",
                        return_value={"formal": project_dir / "ctx.md"},
                    ),
                    patch.object(model_review, "dispatch", return_value=dispatch_result),
                    patch.object(model_review, "find_governance", return_value=None),
                    patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x12"),
                    patch.object(
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
                            "--axes",
                            "formal",
                            "--no-scout",
                        ],
                    ),
                ):
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
                with patch.object(
                    model_review.sys,
                    "argv",
                    [
                        "model-review.py",
                        "--context",
                        str(context_path),
                        "--topic",
                        "invalid",
                        "--project",
                        str(project_dir),
                        "--no-scout",
                        "--verify",
                        "--no-extract",
                    ],
                ):
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
                with patch.object(
                    model_review.sys,
                    "argv",
                    [
                        "model-review.py",
                        "--context",
                        str(context_path),
                        "--topic",
                        "non-gpt",
                        "--project",
                        str(project_dir),
                        "--axes",
                        "arch,domain,alternatives",
                        "--no-scout",
                    ],
                ):
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
                with patch.object(
                    model_review.sys,
                    "argv",
                    [
                        "model-review.py",
                        "--context",
                        str(context_path),
                        "--topic",
                        "bad-questions",
                        "--project",
                        str(project_dir),
                        "--questions",
                        str(questions_path),
                        "--no-scout",
                    ],
                ):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)


class ModelReviewContextBuildTest(unittest.TestCase):
    def test_relative_context_files_resolve_from_project_not_caller_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            (project_dir / "context.txt").write_text("project-owned context")
            foreign_cwd = root / "foreign"
            foreign_cwd.mkdir()

            old_cwd = Path.cwd()
            os.chdir(foreign_cwd)
            try:
                ctx_files = model_review.build_context(
                    review_dir,
                    project_dir,
                    context_file=None,
                    axis_names=["formal"],
                    context_file_specs=["context.txt"],
                )
            finally:
                os.chdir(old_cwd)

            packet = ctx_files["formal"].content_path.read_text()
            self.assertIn("project-owned context", packet)
            self.assertNotIn("read failed", packet)

    def test_declared_missing_context_file_fails_before_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()

            with self.assertRaisesRegex(ValueError, "could not be loaded: missing"):
                model_review.build_context(
                    review_dir,
                    project_dir,
                    context_file=None,
                    axis_names=["formal"],
                    context_file_specs=["missing.md"],
                )

    def test_review_directory_is_owned_by_target_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_dir = root / "project"
            project_dir.mkdir()
            foreign_cwd = root / "foreign"
            foreign_cwd.mkdir()

            old_cwd = Path.cwd()
            os.chdir(foreign_cwd)
            try:
                with patch.object(model_review.os, "urandom", return_value=b"\x01\x02\x03"):
                    review_dir = model_review.create_review_dir(project_dir, "packet ownership")
            finally:
                os.chdir(old_cwd)

            self.assertEqual(review_dir.parent, project_dir / ".model-review")
            self.assertTrue(review_dir.name.endswith("-packet-ownership-010203"))

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


class PremiseScoutTest(unittest.TestCase):
    def test_run_premise_scout_skips_without_binary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            review_dir = Path(td) / "run"
            review_dir.mkdir()
            project = Path(td) / "proj"
            project.mkdir()
            ctx = project / "plan.md"
            ctx.write_text("# plan\nconvert foo() everywhere")
            with patch.object(model_review, "_resolve_cursor_agent_bin", return_value=None):
                result = model_review.run_premise_scout(
                    review_dir=review_dir,
                    project_dir=project,
                    context_path=ctx,
                    topic="foo conversion",
                    question="verify callers",
                )
            self.assertTrue(result.skipped)
            self.assertIsNone(result.conviction)
            self.assertTrue(result.json_path and result.json_path.exists())
            data = json.loads(result.json_path.read_text())
            self.assertTrue(data.get("skipped"))
            self.assertIsNone(data.get("conviction_after"))

    def test_check_scout_conviction_gate_blocks_low_irreversible(self) -> None:
        scout = model_review.PremiseScoutResult(
            skipped=False,
            skip_reason=None,
            markdown_path=Path("/tmp/x.md"),
            json_path=Path("/tmp/x.json"),
            conviction="low",
        )
        self.assertEqual(
            model_review.check_scout_conviction_gate(scout, irreversible=True, force=False),
            3,
        )
        self.assertIsNone(
            model_review.check_scout_conviction_gate(scout, irreversible=True, force=True)
        )
        self.assertIsNone(
            model_review.check_scout_conviction_gate(scout, irreversible=False, force=False)
        )

    def test_check_scout_gate_ignores_skipped(self) -> None:
        scout = model_review.PremiseScoutResult(
            skipped=True,
            skip_reason="no binary",
            markdown_path=None,
            json_path=Path("/tmp/x.json"),
            conviction=None,
        )
        self.assertIsNone(
            model_review.check_scout_conviction_gate(scout, irreversible=True, force=False)
        )

    def test_build_context_includes_premise_scout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            review_dir = Path(td) / "run"
            review_dir.mkdir()
            project = Path(td) / "proj"
            project.mkdir()
            ctx = project / "plan.md"
            ctx.write_text("plan body")
            scout_md = review_dir / "premise-scout.md"
            scout_md.write_text("## Premises checked\n- foo has zero callers")
            ctx_files = model_review.build_context(
                review_dir,
                project,
                ctx,
                ["arch"],
                premise_scout_path=scout_md,
            )
            text = ctx_files["arch"].content_path.read_text()
            self.assertIn("Premise Scout", text)
            self.assertIn("zero callers", text)

    def test_should_run_premise_scout(self) -> None:
        self.assertTrue(
            model_review.should_run_premise_scout(
                scout=True, context_scope="repo", has_context=True
            )
        )
        self.assertFalse(
            model_review.should_run_premise_scout(
                scout=True, context_scope="packet", has_context=True
            )
        )
        self.assertFalse(
            model_review.should_run_premise_scout(
                scout=False, context_scope="repo", has_context=True
            )
        )

    def test_extract_json_block(self) -> None:
        text = 'intro\n```json\n{"fork": "x", "conviction_after": "high"}\n```\n'
        parsed = model_review._extract_json_block(text)
        self.assertEqual(parsed["conviction_after"], "high")


class DispatchBudgetTest(unittest.TestCase):
    def test_no_budget_allows_all(self) -> None:
        budget = model_review.DispatchBudget.from_seconds(None)
        self.assertFalse(budget.active)
        self.assertTrue(budget.can_start(600))

    def test_skip_when_remaining_less_than_profile(self) -> None:
        budget = model_review.DispatchBudget(
            deadline_mono=time.monotonic() + 90,
            total_seconds=480,
        )
        self.assertFalse(budget.can_start(600))

    def test_budget_insufficient_for_profile_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp)
            budget = model_review.DispatchBudget(
                deadline_mono=time.monotonic() + 400,
                total_seconds=480,
            )
            entry = model_review._budget_skipped_axis("arch", rd, budget, profile_timeout=600)
            self.assertEqual(entry["failure_reason"], "budget_insufficient_for_profile")

    def test_axis_budget_restarts_after_scout_phase(self) -> None:
        """Scout wall time must not reduce the axis dispatch budget."""
        budget_before_scout = model_review.DispatchBudget.from_seconds(650)
        rem_before = budget_before_scout.remaining()
        time.sleep(0.05)
        rem_after_scout = budget_before_scout.remaining()
        self.assertLess(rem_after_scout, rem_before)
        budget_for_axes = model_review.DispatchBudget.from_seconds(650)
        self.assertGreater(budget_for_axes.remaining(), rem_after_scout)

    def test_start_when_remaining_fits_profile(self) -> None:
        budget = model_review.DispatchBudget(
            deadline_mono=time.monotonic() + 650,
        )
        self.assertTrue(budget.can_start(600))

    def test_budget_equal_to_profile_timeout_still_starts(self) -> None:
        """Regression: a budget sized EQUAL to the axis timeout (the review_gate triage
        default — 600s budget, deep_review/gpt_general resolve to 600s) must NOT skip.
        Before the start grace, sub-second setup elapsed since from_seconds() left
        remaining fractionally < timeout, so EVERY axis skipped as 'budget_exhausted'
        and the cross-model review produced zero output (genomics 2026-07-01)."""
        budget = model_review.DispatchBudget.from_seconds(600)
        time.sleep(0.02)  # simulate setup elapsed since budget creation
        self.assertLess(budget.remaining(), 600)  # remaining is now fractionally < timeout
        self.assertTrue(budget.can_start(600))  # ...but the start grace lets it dispatch

    def test_wait_timeout_uses_remaining(self) -> None:
        budget = model_review.DispatchBudget(
            deadline_mono=time.monotonic() + 100,
        )
        self.assertGreaterEqual(budget.wait_timeout(1230), 95)
        self.assertLessEqual(budget.wait_timeout(1230), 100)

    def test_apply_dispatch_manifest(self) -> None:
        import argparse

        manifest = {
            "dispatch_policy": {
                "premise_scout": False,
                "context_scope": "packet",
                "budget_seconds": 300,
            },
            "layers": {"design": {"axes": "cross2"}},
            "preset": "cross4",
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(manifest, f)
            path = Path(f.name)
        try:
            args = argparse.Namespace(
                scout=None,
                context_scope=None,
                budget_seconds=None,
                irreversible=False,
                cross_talk=False,
                axes=None,
                extract=None,
                verify=None,
            )
            model_review.apply_dispatch_manifest(args, path)
            self.assertFalse(args.scout)
            self.assertEqual(args.context_scope, "packet")
            self.assertEqual(args.budget_seconds, 300)
            self.assertEqual(args.axes, "cross2")
        finally:
            path.unlink()

    def test_dispatch_manifest_blockers(self) -> None:
        blockers = model_review.dispatch_manifest_blockers(
            {"blockers": ["dead refs in packet: foo.py"]}
        )
        self.assertEqual(len(blockers), 1)

    def test_apply_dispatch_manifest_extract_verify(self) -> None:
        import argparse

        manifest = {
            "dispatch_policy": {},
            "layers": {"design": {"extract": False, "verify": True, "axes": "standard"}},
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(manifest, f)
            path = Path(f.name)
        try:
            args = argparse.Namespace(
                scout=None,
                context_scope=None,
                budget_seconds=None,
                irreversible=False,
                cross_talk=False,
                axes=None,
                extract=None,
                verify=None,
            )
            model_review.apply_dispatch_manifest(args, path)
            self.assertFalse(args.extract)
            self.assertTrue(args.verify)
        finally:
            path.unlink()

    def test_profile_resolved_timeout_high(self) -> None:
        t = model_review._profile_resolved_timeout("formal_review")
        self.assertGreaterEqual(t, 600)

    def test_dispatch_uses_resolved_timeout_for_arch(self) -> None:
        t = model_review._resolved_axis_timeout("arch")
        self.assertGreaterEqual(t, 600)

    def test_write_execution_receipt_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp)
            dispatch_result = {
                "arch": {"exit_code": 0, "size": 100, "model": "gemini"},
                "gaps": {
                    "exit_code": 1,
                    "size": 0,
                    "failure_reason": "budget_exhausted",
                    "budget_remaining_seconds": 30,
                    "profile_timeout": 600,
                },
                "elapsed_seconds": 12.3,
            }
            path = model_review.write_execution_receipt(
                rd,
                axis_names=["arch", "gaps"],
                dispatch_result=dispatch_result,
                effective_policy={"axes": "cross2"},
            )
            receipt = json.loads(path.read_text())
            self.assertEqual(
                receipt["schema_version"], model_review.EXECUTION_RECEIPT_SCHEMA_VERSION
            )
            self.assertEqual(receipt["overall"], "partial")
            self.assertEqual(receipt["axes"]["gaps"]["status"], "skipped_budget")


class PreflightTest(unittest.TestCase):
    @staticmethod
    def _completed(args: list[str], *, exit_code: int, stdout: str) -> object:
        import subprocess

        return subprocess.CompletedProcess(args, exit_code, stdout=stdout, stderr="")

    def _run_preflight(self, probe_payload: dict, *, probe_exit: int) -> tuple[int, dict]:
        import subprocess

        def fake_run(args, **_kwargs):
            if args[1:3] == ["info", "--json"]:
                return self._completed(args, exit_code=0, stdout='{"cli_providers": {}}')
            if args[1:3] == ["chat", "--dry-run"]:
                return self._completed(
                    args,
                    exit_code=0,
                    stdout='{"auth": "subscription", "transport": "claude-cli"}',
                )
            if args[1] == "probe":
                return self._completed(
                    args,
                    exit_code=probe_exit,
                    stdout=json.dumps(probe_payload),
                )
            raise AssertionError(f"unexpected preflight subprocess: {args}")

        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = Path.cwd()
            os.chdir(temp_dir)
            try:
                with (
                    patch("shutil.which", return_value="/usr/bin/llmx"),
                    patch.object(subprocess, "run", side_effect=fake_run),
                ):
                    return_code = model_review.run_preflight(Path(temp_dir))
                payload = json.loads(
                    (Path(temp_dir) / ".model-review/preflight-latest.json").read_text()
                )
            finally:
                os.chdir(old_cwd)
        return return_code, payload

    def test_dry_run_green_does_not_hide_live_quota_failure(self) -> None:
        return_code, payload = self._run_preflight(
            {
                "verdict": "unavailable",
                "cached": False,
                "error_type": "quota_exhausted",
                "status_code": 429,
            },
            probe_exit=6,
        )
        self.assertEqual(return_code, 1)
        self.assertTrue(payload["dry_run_subscription"]["ok"])
        self.assertFalse(payload["live_subscription_entitlement"]["ok"])
        self.assertEqual(payload["live_subscription_entitlement"]["exit_code"], 6)

    def test_live_available_is_required_for_green_preflight(self) -> None:
        return_code, payload = self._run_preflight(
            {
                "verdict": "available",
                "cached": True,
                "checked_at": "2026-07-10T17:36:35+00:00",
                "expires_at": "2026-07-10T17:51:35+00:00",
                "error_type": None,
                "status_code": 0,
            },
            probe_exit=0,
        )
        self.assertEqual(return_code, 0)
        self.assertTrue(payload["live_subscription_entitlement"]["ok"])
        self.assertTrue(payload["live_subscription_entitlement"]["cached"])
        self.assertNotIn("grok_preflight", payload)

    def test_grok_probe_is_opt_in_and_uses_requested_project(self) -> None:
        import subprocess

        def fake_run(args, **_kwargs):
            if args[1:3] == ["info", "--json"]:
                return self._completed(args, exit_code=0, stdout='{"cli_providers": {}}')
            if args[1:3] == ["chat", "--dry-run"]:
                return self._completed(
                    args,
                    exit_code=0,
                    stdout='{"auth": "subscription", "transport": "claude-cli"}',
                )
            if args[1] == "probe":
                return self._completed(
                    args,
                    exit_code=0,
                    stdout='{"verdict": "available", "status_code": 0}',
                )
            raise AssertionError(f"unexpected preflight subprocess: {args}")

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            with (
                patch("shutil.which", return_value="/usr/bin/llmx"),
                patch.object(subprocess, "run", side_effect=fake_run),
                patch.object(
                    model_review,
                    "run_grok_preflight",
                    return_value=(0, {"ok": True, "model": "cursor-grok-4.5-high"}),
                ) as grok_preflight,
            ):
                return_code = model_review.run_preflight(project_dir, include_grok=True)
            payload = json.loads(
                (project_dir / ".model-review/preflight-latest.json").read_text()
            )

        self.assertEqual(return_code, 0)
        grok_preflight.assert_called_once_with(project_dir.resolve())
        self.assertTrue(payload["grok_preflight"]["ok"])


class GrokPreflightTest(unittest.TestCase):
    @staticmethod
    def _completed(args: list[str], *, exit_code: int, stdout: str = "", stderr: str = ""):
        return model_review.subprocess.CompletedProcess(
            args, exit_code, stdout=stdout, stderr=stderr
        )

    def test_exact_registry_and_unrevealed_repo_canary_are_required(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        def fake_cursor(args, **kwargs):
            calls.append((list(args), dict(kwargs)))
            if args[1:] == ["models"]:
                return self._completed(
                    args,
                    exit_code=0,
                    stdout="cursor-grok-4.5-high - Cursor Grok 4.5\n",
                )
            prompt = str(kwargs.get("input_text") or "")
            if "current git commit" in prompt:
                self.assertNotIn("abc123def456", prompt)
                return self._completed(
                    args, exit_code=0, stdout="GROK45_REPO_OK abc123def456\n"
                )
            raise AssertionError(f"unexpected preflight subprocess: {args}")

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            with (
                patch.object(
                    model_review,
                    "_resolve_cursor_agent_bin",
                    return_value="/usr/bin/cursor-agent",
                ),
                patch.object(
                    model_review, "_run_cursor_command", side_effect=fake_cursor
                ) as cursor_run,
                patch.object(
                    model_review.subprocess,
                    "run",
                    return_value=self._completed(
                        ["git"], exit_code=0, stdout="abc123def456\n"
                    ),
                ),
            ):
                return_code, payload = model_review.run_grok_preflight(project_dir)

        self.assertEqual(return_code, 0)
        self.assertTrue(payload["registry"]["exact_slug_present"])
        self.assertTrue(payload["repo_canary"]["response_exact_ok"])
        cursor_dispatches = [args for args, _ in calls if "--model" in args]
        self.assertEqual(len(cursor_dispatches), 1)
        for command in cursor_dispatches:
            self.assertEqual(command[command.index("--mode") + 1], "ask")
            self.assertEqual(
                command[command.index("--model") + 1], "cursor-grok-4.5-high"
            )
            self.assertEqual(
                command[command.index("--workspace") + 1], str(project_dir.resolve())
            )
        cursor_calls = [
            call for call in cursor_run.call_args_list if "--model" in call.args[0]
        ]
        self.assertEqual(len(cursor_calls), 1)
        self.assertTrue(
            all(call.kwargs["cwd"] == project_dir.resolve() for call in cursor_calls)
        )

    def test_missing_exact_registry_slug_stops_before_model_dispatch(self) -> None:
        completed = self._completed(
            ["cursor-agent", "models"],
            exit_code=0,
            stdout="composer-2.5 - Composer 2.5\n",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(
                    model_review,
                    "_resolve_cursor_agent_bin",
                    return_value="/usr/bin/cursor-agent",
                ),
                patch.object(
                    model_review, "_run_cursor_command", return_value=completed
                ) as run,
            ):
                return_code, payload = model_review.run_grok_preflight(Path(temp_dir))

        self.assertEqual(return_code, 1)
        self.assertFalse(payload["registry"]["exact_slug_present"])
        self.assertEqual(run.call_count, 1)

    def test_repo_canary_cannot_pass_by_echoing_a_prompted_hash(self) -> None:
        def fake_cursor(args, **kwargs):
            if args[1:] == ["models"]:
                return self._completed(
                    args,
                    exit_code=0,
                    stdout="cursor-grok-4.5-high - Cursor Grok 4.5\n",
                )
            prompt = str(kwargs.get("input_text") or "")
            self.assertNotIn("abc123def456", prompt)
            return self._completed(
                args, exit_code=0, stdout="GROK45_REPO_OK 000000000000\n"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(
                    model_review,
                    "_resolve_cursor_agent_bin",
                    return_value="/usr/bin/cursor-agent",
                ),
                patch.object(
                    model_review, "_run_cursor_command", side_effect=fake_cursor
                ),
                patch.object(
                    model_review.subprocess,
                    "run",
                    return_value=self._completed(
                        ["git"], exit_code=0, stdout="abc123def456\n"
                    ),
                ),
            ):
                return_code, payload = model_review.run_grok_preflight(Path(temp_dir))

        self.assertEqual(return_code, 1)
        self.assertFalse(payload["repo_canary"]["response_exact_ok"])

    def test_repo_canary_clears_receipts_and_uses_exact_first_twelve(self) -> None:
        full_head = "abc123def4567890abc123def4567890abc123de"

        def fake_cursor(args, **kwargs):
            if args[1:] == ["models"]:
                return self._completed(
                    args,
                    exit_code=0,
                    stdout="cursor-grok-4.5-high - Cursor Grok 4.5\n",
                )
            project_dir = Path(kwargs["cwd"])
            self.assertFalse(
                (project_dir / ".model-review/grok-preflight-latest.json").exists()
            )
            self.assertFalse(
                (project_dir / ".model-review/preflight-latest.json").exists()
            )
            return self._completed(
                args, exit_code=0, stdout="GROK45_REPO_OK abc123def456\n"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            receipt_dir = project_dir / ".model-review"
            receipt_dir.mkdir()
            for name in ("grok-preflight-latest.json", "preflight-latest.json"):
                (receipt_dir / name).write_text(
                    json.dumps({"expected": f"GROK45_REPO_OK {full_head[:12]}"})
                )
            with (
                patch.object(
                    model_review,
                    "_resolve_cursor_agent_bin",
                    return_value="/usr/bin/cursor-agent",
                ),
                patch.object(
                    model_review, "_run_cursor_command", side_effect=fake_cursor
                ),
                patch.object(
                    model_review.subprocess,
                    "run",
                    return_value=self._completed(
                        ["git"], exit_code=0, stdout=f"{full_head}\n"
                    ),
                ) as git_run,
            ):
                return_code, payload = model_review.run_grok_preflight(project_dir)

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["workspace_hygiene"]["prior_receipts_removed"], 2)
        self.assertEqual(payload["repo_head"]["challenge_length"], 12)
        self.assertNotIn(full_head[:12], json.dumps(payload))
        self.assertEqual(
            git_run.call_args.args[0][-3:], ["rev-parse", "--verify", "HEAD"]
        )


class VerifyClaimsAnchorResolutionTest(unittest.TestCase):
    """Regression: a finding citing a leading-slash / absolute path must not crash
    the --verify pass. Python 3.13's Path.rglob raises
    NotImplementedError("Non-relative patterns are unsupported") on a non-relative
    pattern; _filtered_rglob normalizes with lstrip('/'). The structured `file` field
    bypasses the body-regex (which requires a relative start), so it is the path that
    reaches the resolver with a leading slash. Bug: /critique close 2026-06-18 — a
    "/eval/SKILL.md" anchor aborted the whole verify pass after extraction.
    """

    def _verify_one(self, file_anchor: str, project_dir: str, sibling_roots=None) -> Path:
        review_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(review_dir, ignore_errors=True))
        (review_dir / "findings.json").write_text(
            json.dumps(
                {
                    "findings": [
                        {
                            "id": 1,
                            "title": "leading-slash anchor",
                            "file": file_anchor,
                            "line": 0,
                            "description": "d",
                            "fix": "f",
                        }
                    ]
                }
            )
        )
        disp = review_dir / "disposition.md"
        disp.write_text("# Review Findings\n\n1. **[HIGH]** leading-slash anchor\n")
        out = model_review.verify_claims(
            review_dir, str(disp), Path(project_dir), sibling_roots=sibling_roots or []
        )
        return Path(out)

    def test_leading_slash_anchor_does_not_crash_verify(self) -> None:
        # Pre-fix this raised NotImplementedError and aborted the whole pass.
        with tempfile.TemporaryDirectory() as proj:
            out = self._verify_one("/eval/SKILL.md", proj)
            self.assertTrue(out.exists())
            self.assertEqual(out.name, "verified-disposition.md")

    def test_leading_slash_with_sibling_root_does_not_crash(self) -> None:
        # The original crash path was invoked with --sibling-roots; the sibling
        # basename search is also routed through _filtered_rglob.
        with tempfile.TemporaryDirectory() as proj, tempfile.TemporaryDirectory() as sib:
            out = self._verify_one("/eval/SKILL.md", proj, sibling_roots=[Path(sib)])
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
