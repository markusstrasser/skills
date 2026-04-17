#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Deep review (4 queries: arch + formal + domain + mechanical)
    model-review.py --context plan.md --topic "classification logic" --axes arch,formal,domain,mechanical "Review this"

    # With project dir for constitution discovery
    model-review.py --context plan.md --topic "data wiring" --project ~/Projects/intel "Review this plan"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _reexec_under_llmx_python_if_needed() -> None:
    # `uv run python3 model-review.py` inherits the caller project's venv Python.
    # If that Python can't import llmx (typical: 3.12 caller vs 3.13 tool install),
    # _bootstrap_llmx() later raises ImportError and the user has to restart by
    # hand. Re-exec transparently under the llmx tool's own Python instead.
    try:
        import llmx  # type: ignore  # noqa: F401
        return
    except ImportError:
        pass
    llmx_py = Path.home() / ".local/share/uv/tools/llmx/bin/python3"
    if not llmx_py.exists():
        return
    try:
        if Path(sys.executable).resolve() == llmx_py.resolve():
            return
    except OSError:
        return
    os.execv(str(llmx_py), [str(llmx_py), str(Path(__file__).resolve()), *sys.argv[1:]])


_reexec_under_llmx_python_if_needed()

import shared.llm_dispatch as dispatch_core
from shared.context_budget import enforce_budget
from shared.context_packet import BudgetPolicy, ContextPacket, FileBlock, PacketSection, TextBlock
from shared.context_preamble import build_review_preamble_blocks, find_constitution as shared_find_constitution
from shared.context_renderers import write_packet_artifact
from shared.file_specs import parse_file_spec, read_file_excerpt

# --- Structured output schema (both models return this) ---

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["bug", "logic", "architecture", "missing", "performance", "security", "style", "constitutional"],
                    },
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "title": {"type": "string", "description": "One-line summary"},
                    "description": {"type": "string", "description": "Detailed explanation with evidence"},
                    "file": {"type": "string", "description": "File path if cited, empty if architectural"},
                    "line": {"type": "integer", "description": "Line number if cited, 0 if N/A"},
                    "fix": {"type": "string", "description": "Proposed fix, empty if unclear"},
                    "confidence": {"type": "number", "description": "0.0-1.0 confidence in this finding"},
                },
                "required": ["category", "severity", "title", "description", "file", "line", "fix", "confidence"],
            },
        },
    },
    "required": ["findings"],
}

# --- Axis definitions: model + prompt + api kwargs ---

AXES = {
    "arch": {
        "label": "Gemini (architecture/patterns)",
        "profile": "deep_review",
        "prompt": """\
<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code, configs, and findings. It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
{constitution_instruction}

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?""",
    },
    "formal": {
        "label": "GPT-5.4 (quantitative/formal)",
        "profile": "formal_review",
        "prompt": """\
<system>
You are performing QUANTITATIVE and FORMAL analysis. Other reviewers handle qualitative pattern review. Focus on what they can't do well. Be precise. Show your reasoning. No hand-waving.
Budget: ~2000 words. Tables over prose. Source-grade claims.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
{constitution_instruction}

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.""",
    },
    "domain": {
        "label": "Gemini Pro (domain correctness)",
        "profile": "deep_review",
        "prompt": """\
<system>
You are verifying DOMAIN-SPECIFIC CLAIMS in this plan. Other reviewers handle architecture and formal logic.
Focus exclusively on: are the domain facts correct? Are citations real? Are API endpoints, database schemas,
biological claims, financial numbers accurate? Check every specific claim against your knowledge.
Budget: ~1500 words. Flat list of claims with verdict (CORRECT / WRONG / UNVERIFIABLE).
</system>

{question}

For each domain-specific claim in the reviewed material:
1. State the claim
2. Verdict: CORRECT / WRONG / UNVERIFIABLE
3. If WRONG: what's actually true
4. If UNVERIFIABLE: what would you need to check

Flag any URLs, API endpoints, or version numbers that should be probed before implementation.""",
    },
    "mechanical": {
        "label": "Gemini Flash (mechanical audit)",
        "profile": "fast_extract",
        "prompt": """\
<system>
Mechanical audit only. No analysis, no recommendations. Fast and precise.
</system>

Find in the reviewed material:
- Stale references (wrong versions, deprecated APIs, broken links)
- Inconsistent naming (model names, paths, conventions that don't match)
- Missing cross-references between related documents
- Duplicated content
- Paths or file references that look wrong
Output as a flat numbered list. One issue per line.""",
    },
    "alternatives": {
        "label": "Gemini Pro (alternative approaches)",
        "profile": "deep_review",
        "prompt": """\
<system>
You are generating ALTERNATIVE APPROACHES to the proposed plan. Other reviewers check correctness.
Your job: what ELSE could be done? Different mechanisms, not variations.
Budget: ~1500 words.
</system>

{question}

Generate 3-5 genuinely different approaches to the same problem. For each:
1. Core mechanism (how it works differently)
2. What it's better at than the proposed approach
3. What it's worse at
4. Maintenance burden and complexity cost (not implementation effort — agents build everything)

Do NOT critique the existing plan — generate alternatives. Different mechanisms, not tweaks.""",
    },
}

# Presets map a single name to a list of axes
PRESETS = {
    "standard": ["arch", "formal"],
    "deep": ["arch", "formal", "domain", "mechanical"],
    "full": ["arch", "formal", "domain", "mechanical", "alternatives"],
}

GEMINI_PRO_MODEL = dispatch_core.PROFILES["deep_review"].model
GEMINI_FLASH_MODEL = dispatch_core.PROFILES["fast_extract"].model
COVERAGE_SCHEMA_VERSION = "review-coverage.v1"
GEMINI_RATE_LIMIT_MARKERS = (
    "503",
    "rate limit",
    "rate-limit",
    "resource_exhausted",
    "overloaded",
    "429",
)


class ContextArtifact(NamedTuple):
    content_path: Path
    manifest_path: Path


def context_content_path(value: Path | ContextArtifact) -> Path:
    return value.content_path if isinstance(value, ContextArtifact) else value


def context_manifest_path(value: Path | ContextArtifact) -> Path | None:
    return value.manifest_path if isinstance(value, ContextArtifact) else None


def axis_uses_gpt(axis_name: str) -> bool:
    model_name = dispatch_core.PROFILES[str(AXES[axis_name]["profile"])].model.lower()
    return "gpt" in model_name


def resolve_axes(raw_axes: str, *, allow_non_gpt: bool = False) -> list[str]:
    axes_text = raw_axes.strip()
    if axes_text == "simple":
        raise ValueError("the `simple` preset was removed; use `standard` for the GPT-inclusive default")

    if axes_text in PRESETS:
        axis_names = PRESETS[axes_text]
    else:
        axis_names = [axis.strip() for axis in axes_text.split(",") if axis.strip()]
        if not axis_names:
            raise ValueError("no review axes provided")
        unknown_axes = [axis for axis in axis_names if axis not in AXES]
        if unknown_axes:
            raise ValueError(
                f"unknown axis '{unknown_axes[0]}'. Available: {', '.join(sorted(AXES.keys()))}"
            )

    if not allow_non_gpt and not any(axis_uses_gpt(axis_name) for axis_name in axis_names):
        raise ValueError(
            "review requires at least one GPT-backed axis; add `formal` or use `standard`, `deep`, or `full`"
        )
    return axis_names


def slugify(text: str, max_len: int = 40) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


# Prompts that are almost certainly slash-command-mode leakage rather than a
# real review question. Passing these verbatim to the model produces generic
# "looks good to me" synthesis because the model has no attack surface. Two
# genomics sessions on 2026-04-16 dispatched with `"close"` and got weak output.
_UNDERSPECIFIED_PROMPTS = {
    "close", "review", "verify", "check", "model", "deep", "full",
    "standard", "model-review", "critique", "audit", "fix",
}


def _rewrite_underspecified_prompt(question: str, topic: str) -> str:
    """Replace slash-command-mode verbs with a structured adversarial prompt.

    Returns the original question unchanged if it looks like a real prompt
    (> 30 chars or multi-clause). Otherwise substitutes a template that invites
    concrete attack surface against the supplied topic.
    """
    q = (question or "").strip()
    single_token = q.lower().strip(" .?!:-")
    too_short = len(q) < 25 and " " not in q.strip()
    is_verb = single_token in _UNDERSPECIFIED_PROMPTS
    if not (too_short or is_verb):
        return question
    print(
        f"warning: positional prompt {q!r} looks like slash-command leakage; "
        f"substituting a structured adversarial template. Pass a concrete "
        f"review question to silence this.",
        file=sys.stderr,
    )
    return (
        f"Adversarial review of: {topic}. "
        f"(1) For each touched file in the context packet, name one concrete "
        f"bug, logic error, missing edge case, or boundary-condition failure. "
        f"Cite file and line. "
        f"(2) Flag any claim in the diff that contradicts the surrounding "
        f"code (silent semantic failure). "
        f"(3) Identify tests that would pass on the committed code but "
        f"would NOT catch a plausible regression — what's the blind spot? "
        f"(4) Call out compatibility scaffolding, dual-paths, or wrappers "
        f"that should be deleted under the default breaking-refactor stance. "
        f"(5) If you find nothing substantial, say so explicitly — do not "
        f"manufacture findings."
    )


def _add_additional_properties(schema: dict) -> dict:
    """Recursively add additionalProperties:false to all objects (OpenAI strict mode)."""
    import copy

    transformed = copy.deepcopy(schema)

    def walk(obj: dict) -> None:
        if obj.get("type") == "object":
            obj["additionalProperties"] = False
        for value in obj.values():
            if isinstance(value, dict):
                walk(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        walk(item)

    walk(transformed)
    return transformed


def _strip_additional_properties(schema: dict) -> dict:
    """Recursively remove additionalProperties from all objects (Google API)."""
    import copy

    transformed = copy.deepcopy(schema)

    def walk(obj: dict) -> None:
        obj.pop("additionalProperties", None)
        for value in obj.values():
            if isinstance(value, dict):
                walk(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        walk(item)

    walk(transformed)
    return transformed


def _call_llmx(
    provider: str,
    model: str,
    context_path: Path,
    prompt: str,
    output_path: Path,
    context_manifest_path: Path | None = None,
    schema: dict | None = None,
    **kwargs,
) -> dict:
    """Call the shared dispatch helper and adapt its result shape for review logic."""
    try:
        profile = dispatch_core.map_model_to_profile(model)
        override_payload = {}
        for key in ("timeout", "reasoning_effort", "max_tokens", "search"):
            if key in kwargs and kwargs[key] is not None:
                override_payload[key] = kwargs[key]
        overrides = dispatch_core.DispatchOverrides(**override_payload) if override_payload else None
        result = dispatch_core.dispatch(
            profile=profile,
            prompt=prompt,
            context_path=context_path,
            context_manifest_path=context_manifest_path,
            output_path=output_path,
            schema=schema,
            overrides=overrides,
            api_only=True,
        )
        output_size = output_path.stat().st_size if output_path.exists() else 0
        exit_code = 0 if result.status in {"ok", "parse_error"} else 1
        return {
            "exit_code": exit_code,
            "size": output_size,
            "latency": result.latency,
            "error": result.error_message,
        }
    except Exception as e:
        error_msg = str(e)[:500]
        print(f"warning: llmx call failed ({model}): {error_msg}", file=sys.stderr)
        return {
            "exit_code": 1,
            "size": 0,
            "latency": 0,
            "error": error_msg,
        }


def axis_output_failed(info: object) -> bool:
    """Return True when an axis failed to produce a usable review artifact."""
    if not isinstance(info, dict):
        return False
    return int(info.get("exit_code", 0)) != 0 or int(info.get("size", 0)) == 0


def collect_dispatch_failures(
    dispatch_result: dict,
    ctx_files: dict[str, Path | ContextArtifact],
) -> list[dict[str, object]]:
    """Summarize failed axes for machine-readable failure artifacts."""
    failures: list[dict[str, object]] = []
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}
    for axis, info in dispatch_result.items():
        if axis in skip_keys or not axis_output_failed(info):
            continue
        entry = dict(info)
        entry["axis"] = axis
        entry["context"] = str(context_content_path(ctx_files[axis])) if axis in ctx_files else ""
        entry["failure_reason"] = (
            "nonzero_exit" if int(entry.get("exit_code", 0)) != 0 else "empty_output"
        )
        failures.append(entry)
    return failures


def rerun_axis_with_flash(
    axis: str,
    axis_def: dict[str, object],
    review_dir: Path,
    ctx_file: Path | ContextArtifact,
    prompt: str,
) -> dict:
    """Retry a failed Gemini Pro axis with Gemini Flash."""
    out_path = review_dir / f"{axis}-output.md"
    print(
        f"warning: {axis} hit Gemini Pro rate limits; retrying once with Gemini Flash",
        file=sys.stderr,
    )
    api_kwargs = dict(axis_def.get("api_kwargs") or {})  # type: ignore[arg-type]
    return _call_llmx(
        provider="google",
        model=GEMINI_FLASH_MODEL,
        context_path=context_content_path(ctx_file),
        context_manifest_path=context_manifest_path(ctx_file),
        prompt=prompt,
        output_path=out_path,
        **api_kwargs,
    )


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    return shared_find_constitution(project_dir)


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
    *,
    context_file_specs: list[str] | None = None,
    budget_limit_override: int | None = None,
) -> dict[str, ContextArtifact]:
    """Assemble shared context packet with constitutional preamble.

    Context sources (in order of precedence):
      1. --context FILE — single pre-assembled context file
      2. --context-files spec1 spec2 ... — auto-assembled from file:range specs
    """
    preamble_blocks, _ = build_review_preamble_blocks(project_dir)
    packet_sections = [PacketSection("Preamble", preamble_blocks)]

    if context_file:
        packet_sections.append(
            PacketSection(
                "Provided Context",
                [TextBlock(str(context_file), context_file.read_text(), priority=400, drop_if_needed=False, metadata={"path": str(context_file)})],
            )
        )
    elif context_file_specs:
        file_blocks = []
        for spec_text in context_file_specs:
            spec = parse_file_spec(spec_text.strip())
            excerpt, truncated, omission_reason = read_file_excerpt(spec, max_chars=None)
            metadata: dict[str, object] = {}
            if omission_reason:
                metadata["omission_reason"] = omission_reason
            file_blocks.append(
                FileBlock(
                    spec.display_path,
                    excerpt,
                    range_spec=spec.range_spec,
                    priority=40,
                    drop_if_needed=True,
                    min_chars=1_000,
                    truncated=truncated,
                    truncation_reason="file_range_excerpt" if truncated else None,
                    metadata=metadata,
                )
            )
        packet_sections.append(PacketSection("Context Files", file_blocks))
    else:
        packet_sections.append(PacketSection("Provided Context", [TextBlock("Context", "", priority=10, drop_if_needed=True)]))

    token_limits = [
        dispatch_core.profile_input_budget(AXES[axis]["profile"])["input_token_limit"]
        for axis in axis_names
        if dispatch_core.profile_input_budget(AXES[axis]["profile"])["input_token_limit"] is not None
    ]
    budget_limit = budget_limit_override if budget_limit_override is not None else (min(token_limits) if token_limits else 120000)
    packet = ContextPacket(
        title="Model Review Context Packet",
        sections=packet_sections,
        metadata={"Project": str(project_dir), "Axes": ",".join(axis_names)},
        budget_policy=BudgetPolicy(metric="tokens", limit=budget_limit),
    )
    packet = enforce_budget(packet, renderer="markdown").packet

    content_path = review_dir / "shared-context.md"
    manifest_path = review_dir / "shared-context.manifest.json"
    artifact = write_packet_artifact(
        packet,
        renderer="markdown",
        output_path=content_path,
        manifest_path=manifest_path,
        builder_name="model_review_context",
        builder_version="2026-04-10-v1",
    )
    if artifact.rendered_bytes > 15_000:
        print(
            f"warning: shared context {artifact.rendered_bytes} bytes "
            f"({artifact.token_estimate} tokens est.) may be large",
            file=sys.stderr,
        )
    return {axis: ContextArtifact(content_path=content_path, manifest_path=manifest_path) for axis in axis_names}


def dispatch(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_constitution: bool,
    question_overrides: dict[str, str] | None = None,
) -> dict:
    """Fire N llmx API calls in parallel (one per axis), wait, return results."""
    today = date.today().isoformat()

    const_instruction = {
        "arch": (
            "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?"
            if has_constitution
            else "No constitution provided — assess internal consistency only."
        ),
        "formal": (
            "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes."
            if has_constitution
            else "No constitution provided — assess internal logical consistency."
        ),
    }

    prompts: dict[str, str] = {}
    t0 = time.time()

    for axis in axis_names:
        axis_def = AXES[axis]
        axis_question = (question_overrides or {}).get(axis, question)
        prompts[axis] = axis_def["prompt"].format(
            date=today,
            question=axis_question,
            constitution_instruction=const_instruction.get(axis, ""),
        )

    def _run_axis(axis: str) -> tuple[str, dict]:
        axis_def = AXES[axis]
        profile_name = str(axis_def["profile"])
        profile_def = dispatch_core.PROFILES[profile_name]
        out_path = review_dir / f"{axis}-output.md"
        context_artifact = ctx_files[axis]
        result = _call_llmx(
            provider=profile_def.provider,
            model=profile_def.model,
            context_path=context_content_path(context_artifact),
            context_manifest_path=context_manifest_path(context_artifact),
            prompt=prompts[axis],
            output_path=out_path,
        )
        entry = {
            "label": axis_def["label"],
            "requested_model": profile_def.model,
            "model": profile_def.model,
            "exit_code": result["exit_code"],
            "output": str(out_path),
            "size": result["size"],
        }
        if result.get("latency"):
            entry["latency"] = result["latency"]
        if result.get("error"):
            entry["stderr"] = result["error"]

        # Gemini Pro fallback to Flash on rate limit
        if (
            profile_def.model == GEMINI_PRO_MODEL
            and result["exit_code"] != 0
            and result.get("error")
            and any(m in result["error"].lower() for m in GEMINI_RATE_LIMIT_MARKERS)
        ):
            entry["fallback_from"] = profile_def.model
            entry["fallback_reason"] = "gemini_rate_limit"
            entry["initial_exit_code"] = result["exit_code"]
            flash_result = rerun_axis_with_flash(
                axis, axis_def, review_dir, ctx_files[axis], prompts[axis],
            )
            entry["model"] = GEMINI_FLASH_MODEL
            entry["exit_code"] = flash_result["exit_code"]
            entry["size"] = flash_result["size"]
            if flash_result.get("latency"):
                entry["latency"] = flash_result["latency"]
            entry.pop("stderr", None)
            if flash_result.get("error"):
                entry["stderr"] = flash_result["error"]

        if entry["size"] == 0:
            entry["failure_reason"] = "empty_output"

        return axis, entry

    # Parallel dispatch via threads
    results: dict = {"review_dir": str(review_dir), "axes": axis_names, "queries": len(axis_names)}
    with ThreadPoolExecutor(max_workers=len(axis_names)) as pool:
        futures = {pool.submit(_run_axis, axis): axis for axis in axis_names}
        try:
            for future in as_completed(futures, timeout=720):
                axis, entry = future.result()
                results[axis] = entry
        except TimeoutError:
            # as_completed raises at iterator level when global timeout expires
            for future, axis in futures.items():
                if axis not in results:
                    results[axis] = {
                        "label": AXES[axis]["label"],
                        "requested_model": dispatch_core.PROFILES[str(AXES[axis]["profile"])].model,
                        "model": dispatch_core.PROFILES[str(AXES[axis]["profile"])].model,
                        "exit_code": 1,
                        "output": str(review_dir / f"{axis}-output.md"),
                        "size": 0,
                        "failure_reason": "thread_timeout",
                    }

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _review_artifact_path(review_dir: Path, filename: str) -> str | None:
    path = review_dir / filename
    return str(path) if path.exists() else None


def _context_packet_summary(review_dir: Path) -> dict[str, object]:
    manifest_path = review_dir / "shared-context.manifest.json"
    manifest = _load_json(manifest_path)
    packet_metadata = manifest.get("packet_metadata") or {}
    budget_enforcement = packet_metadata.get("budget_enforcement") or {}
    return {
        "path": str(manifest_path) if manifest_path.exists() else None,
        "builder_name": manifest.get("builder_name"),
        "builder_version": manifest.get("builder_version"),
        "payload_hash": manifest.get("payload_hash"),
        "rendered_content_hash": manifest.get("rendered_content_hash"),
        "rendered_bytes": manifest.get("rendered_bytes"),
        "token_estimate": manifest.get("token_estimate"),
        "estimate_method": manifest.get("estimate_method"),
        "budget_metric": manifest.get("budget_metric"),
        "budget_limit": manifest.get("budget_limit"),
        "source_paths_count": len(manifest.get("source_paths") or []),
        "truncation_event_count": len(manifest.get("truncation_events") or []),
        "dropped_blocks": budget_enforcement.get("dropped_blocks") or [],
    }


def write_coverage_artifact(
    review_dir: Path,
    dispatch_result: dict | None = None,
    *,
    extraction_tasks: list[tuple[str, Path, str]] | None = None,
    axis_findings: dict[str, list[dict]] | None = None,
    merged_findings: list[dict] | None = None,
    disposition_path: str | None = None,
    verification_summary: dict[str, object] | None = None,
    verified_disposition_path: str | None = None,
) -> Path:
    coverage_path = review_dir / "coverage.json"
    existing_payload = _load_json(coverage_path)
    requested_axes: list[str] = []
    dispatch_axes: list[dict[str, object]] = []

    if dispatch_result is not None:
        requested_axes = [str(axis) for axis in dispatch_result.get("axes", []) if isinstance(axis, str)]
        if not requested_axes:
            requested_axes = [
                axis
                for axis, info in dispatch_result.items()
                if axis
                not in {"review_dir", "axes", "queries", "elapsed_seconds", "dispatch_failures", "failed_axes"}
                and isinstance(info, dict)
            ]
        dispatch_axes = [
            {
                "axis": axis,
                "label": info.get("label"),
                "requested_model": info.get("requested_model"),
                "model": info.get("model"),
                "exit_code": info.get("exit_code"),
                "output_path": info.get("output"),
                "output_bytes": info.get("size"),
                "latency_seconds": info.get("latency"),
                "fallback_from": info.get("fallback_from"),
                "fallback_reason": info.get("fallback_reason"),
            }
            for axis, info in ((axis, dispatch_result[axis]) for axis in requested_axes)
        ]

    payload = {
        "schema": COVERAGE_SCHEMA_VERSION,
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "review_dir": str(review_dir),
        "artifacts": existing_payload.get("artifacts", {}),
        "context_packet": _context_packet_summary(review_dir),
        "dispatch": existing_payload.get("dispatch", {}),
        "extraction": existing_payload.get("extraction", {"enabled": False}),
        "verification": existing_payload.get("verification", {"enabled": False}),
    }

    payload["artifacts"].update(
        {
            "shared_context": _review_artifact_path(review_dir, "shared-context.md"),
            "shared_context_manifest": _review_artifact_path(review_dir, "shared-context.manifest.json"),
            "findings": _review_artifact_path(review_dir, "findings.json"),
            "disposition": disposition_path or payload["artifacts"].get("disposition"),
            "verified_disposition": verified_disposition_path or payload["artifacts"].get("verified_disposition"),
        }
    )

    if dispatch_result is not None:
        payload["dispatch"] = {
            "requested_axes": requested_axes,
            "requested_axis_count": len(requested_axes),
            "axes": dispatch_axes,
            "elapsed_seconds": dispatch_result.get("elapsed_seconds"),
        }

    if extraction_tasks is not None or axis_findings is not None or merged_findings is not None:
        usable_axes = [axis for axis, _, _ in (extraction_tasks or [])]
        usable_axis_count = len(usable_axes)
        findings_before_dedup = sum(len(findings) for findings in (axis_findings or {}).values())
        payload["extraction"] = {
            "enabled": True,
            "usable_axes": usable_axes,
            "usable_axis_count": usable_axis_count,
            "axes_with_findings": list((axis_findings or {}).keys()),
            "axes_with_findings_count": len(axis_findings or {}),
            "findings_before_dedup": findings_before_dedup,
            "findings_after_dedup": len(merged_findings or []),
            "cross_model_agreements": sum(
                1 for finding in (merged_findings or []) if finding.get("cross_model")
            ),
            "findings_by_axis": {
                axis: len(findings) for axis, findings in (axis_findings or {}).items()
            },
            "coverage_ratio": round(len(axis_findings or {}) / usable_axis_count, 3) if usable_axis_count else 0.0,
        }

    if verification_summary is not None:
        payload["verification"] = {"enabled": True, **verification_summary}

    coverage_path.write_text(json.dumps(payload, indent=2) + "\n")
    return coverage_path


EXTRACTION_PROMPT = (
    "Extract every discrete recommendation, finding, or claimed bug from the review. "
    "Return JSON matching the schema. For each finding: category, severity, a one-line title, "
    "description with the reviewer's evidence, file path if cited, proposed fix, "
    "and confidence 0.0-1.0 based on specificity of evidence. "
    "SKIP confirmatory observations that merely describe correct behavior. "
    "Only extract items that propose a change, flag a problem, or claim something is wrong/missing."
)


_UNCALIBRATED_RE = re.compile(
    r"(?:"
    r"(?:≥|>=|>|at least|minimum|must exceed)\s*(\d+(?:\.\d+)?)\s*"  # op NUMBER unit
    r"(?:%|pp|percentage points?|AUPRC|AUROC|PPV|NPV|F1|AUC)"
    r"|"
    r"(?:AUPRC|AUROC|PPV|NPV|F1|AUC)\s*(?:\w+\s+)?(?:≥|>=|>)\s*(\d+(?:\.\d+)?)"  # UNIT [by] op NUMBER
    r"|"
    r"(?:≥|>=|>)\s*(\d+(?:\.\d+)?)\s*(?:%|pp)[/,]"  # ≥95%/ or ≥50%, (slash-separated thresholds)
    r")",
    re.IGNORECASE,
)

# Source indicators — if these appear near the number, it's probably calibrated
_SOURCE_INDICATORS = re.compile(
    r"(?:paper|study|benchmark|calibrat|empirical|measured|observed|from\s+\w+\s+\d{4}|"
    r"doi|PMID|arXiv|Table\s+\d|Figure\s+\d|Supplementary)",
    re.IGNORECASE,
)


def _flag_uncalibrated_thresholds(text: str) -> str:
    """Flag numeric threshold claims that lack cited sources.

    Adds [UNCALIBRATED] tag to lines with threshold operators (≥X%, PPV ≥0.8)
    that don't mention a paper, benchmark, or empirical source nearby.
    """
    lines = text.split("\n")
    flagged = []
    for line in lines:
        if _UNCALIBRATED_RE.search(line) and not _SOURCE_INDICATORS.search(line):
            if "[UNCALIBRATED]" not in line:
                line = line.rstrip() + " [UNCALIBRATED]"
        flagged.append(line)
    return "\n".join(flagged)


def extract_claims(
    review_dir: Path,
    dispatch_result: dict,
) -> str | None:
    """Cross-family extraction: Flash extracts GPT outputs, GPT-Instant extracts Gemini outputs.

    Returns path to disposition.md, or None if no outputs to extract.
    Writes coverage.json whenever extraction tasks were attempted.
    """
    extraction_tasks: list[tuple[str, Path, str]] = []  # (axis, output_path, profile)
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}

    for axis, info in dispatch_result.items():
        if axis in skip_keys or not isinstance(info, dict):
            continue
        if info.get("size", 0) == 0:
            continue

        output_path = Path(info["output"])
        if not output_path.exists():
            continue

        model = info.get("model", "")

        # Cross-family: Gemini outputs → GPT extraction, GPT outputs → Gemini Flash extraction
        if "gemini" in model.lower():
            extraction_tasks.append((axis, output_path, "gpt_general"))
        else:
            extraction_tasks.append((axis, output_path, "fast_extract"))

    if not extraction_tasks:
        return None

    print(
        f"Extracting claims from {len(extraction_tasks)} outputs...",
        file=sys.stderr,
    )

    def _extract_one(task: tuple[str, Path, str]) -> tuple[str, list[dict] | None]:
        axis, output_path, profile = task
        profile_def = dispatch_core.PROFILES[profile]
        extraction_path = review_dir / f"{axis}-extraction.json"
        result = _call_llmx(
            provider=profile_def.provider,
            model=profile_def.model,
            context_path=output_path,
            context_manifest_path=None,
            prompt=EXTRACTION_PROMPT,
            output_path=extraction_path,
            schema=FINDING_SCHEMA,
        )
        if result["exit_code"] != 0:
            print(f"warning: extraction for {axis} failed: {result.get('error', 'unknown')}", file=sys.stderr)
            return axis, None
        if result["size"] > 0:
            try:
                raw = extraction_path.read_text().strip()
                # Strip markdown fences (```json ... ```) that models sometimes add
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
                    raw = re.sub(r"\n?```\s*$", "", raw)
                data = json.loads(raw)
                return axis, data.get("findings", [])
            except (json.JSONDecodeError, KeyError) as e:
                print(f"warning: extraction for {axis} returned invalid JSON: {e}", file=sys.stderr)
                # Fall back to raw text
                return axis, None
        print(f"warning: extraction for {axis} produced empty output", file=sys.stderr)
        return axis, None

    # Parallel extraction
    axis_findings: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(extraction_tasks)) as pool:
        for axis, findings in pool.map(_extract_one, extraction_tasks):
            if findings:
                axis_findings[axis] = findings

    if not axis_findings:
        write_coverage_artifact(
            review_dir,
            dispatch_result,
            extraction_tasks=extraction_tasks,
            axis_findings={},
            merged_findings=[],
        )
        return None

    # Merge findings across axes — keyword overlap for cross-model dedup
    def _fingerprint(f: dict) -> set[str]:
        """Extract significant keywords for fuzzy matching."""
        text = f"{f.get('title', '')} {f.get('file', '')} {f.get('description', '')[:200]}"
        words = set(re.findall(r"[a-z_]{4,}", text.lower()))
        # Remove common stop-words that inflate false matches
        words -= {"this", "that", "with", "from", "should", "could", "would", "does", "have", "will", "also", "been"}
        return words

    merged_findings: list[dict] = []
    seen: list[tuple[set[str], dict]] = []  # (keywords, finding)
    for axis, findings in axis_findings.items():
        source_label = dispatch_result[axis].get("label", axis)
        source_model = dispatch_result[axis].get("model", "unknown")
        for f in findings:
            f["source_axis"] = axis
            f["source_model"] = source_model
            f["source_label"] = source_label
            fp = _fingerprint(f)
            # Check for overlap with existing findings (Jaccard > 0.3)
            matched = False
            for existing_fp, existing in seen:
                if len(fp & existing_fp) > 0 and len(fp & existing_fp) / len(fp | existing_fp) > 0.3:
                    existing.setdefault("also_found_by", []).append(source_label)
                    existing["cross_model"] = True
                    existing["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.2)
                    matched = True
                    break
            if not matched:
                seen.append((fp, f))
                merged_findings.append(f)

    # Sort: cross-model agreements first, then by severity, then confidence
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    merged_findings.sort(key=lambda f: (
        0 if f.get("cross_model") else 1,
        severity_order.get(f.get("severity", "low"), 3),
        -(f.get("confidence", 0)),
    ))

    # Renumber
    for i, f in enumerate(merged_findings, 1):
        f["id"] = i

    # Write structured JSON
    structured_path = review_dir / "findings.json"
    structured_path.write_text(json.dumps({"findings": merged_findings}, indent=2) + "\n")

    # Write human-readable disposition
    extractions: list[str] = []
    for f in merged_findings:
        source = f.get("source_label", "unknown")
        also = f.get("also_found_by", [])
        agreement = f" **[CROSS-MODEL: also {', '.join(also)}]**" if also else ""
        conf = f.get("confidence", 0)
        extractions.append(
            f"{f['id']}. **[{f.get('severity', '?').upper()}]** {f.get('title', '?')}{agreement}\n"
            f"   Category: {f.get('category', '?')} | Confidence: {conf:.1f} | Source: {source}\n"
            f"   {f.get('description', '')}\n"
            f"   File: {f.get('file', 'N/A')}\n"
            f"   Fix: {f.get('fix', 'N/A')}"
        )

    if not extractions:
        return None

    disposition = review_dir / "disposition.md"
    merged = "\n\n---\n\n".join(extractions)

    # Flag uncalibrated thresholds — numeric claims without cited sources
    merged = _flag_uncalibrated_thresholds(merged)

    response_template = (
        "\n\n---\n\n"
        "## Agent Response (fill before implementing)\n\n"
        "### Where I disagree with the disposition:\n"
        '<!-- "Nowhere" is valid. Don\'t invent disagreements. -->\n\n\n'
        "### Context I had that the models didn't:\n"
        "<!-- If context file was comprehensive, say so. -->\n\n"
    )
    cross_model_count = sum(1 for f in merged_findings if f.get("cross_model"))
    header = (
        f"# Review Findings — {date.today().isoformat()}\n\n"
        f"**{len(merged_findings)} findings** from {len(axis_findings)} axes"
        f" ({cross_model_count} cross-model agreements)\n"
        f"Structured data: `findings.json`\n\n"
    )
    disposition.write_text(header + merged + response_template)
    write_coverage_artifact(
        review_dir,
        dispatch_result,
        extraction_tasks=extraction_tasks,
        axis_findings=axis_findings,
        merged_findings=merged_findings,
        disposition_path=str(disposition),
    )
    return str(disposition)


def verify_claims(
    review_dir: Path,
    disposition_path: str,
    project_dir: Path,
) -> str:
    """Verify extracted claims against the actual codebase.

    Checks if cited files and symbols exist. Grades each claim:
    - CONFIRMED: all cited files/symbols found
    - HALLUCINATED: cited file does not exist in project
    - UNVERIFIABLE: no file references to check

    Returns path to verified-disposition.md.
    """
    disposition_text = Path(disposition_path).read_text()

    def _parse_disposition_claims() -> list[dict[str, object]]:
        parsed_claims: list[dict[str, object]] = []
        current_section = ""
        current_claim: dict[str, object] | None = None
        current_lines: list[str] = []
        for raw_line in disposition_text.splitlines():
            line = raw_line.rstrip()
            section_match = re.match(r"^##\s+(.+)", line)
            if section_match:
                if current_claim is not None:
                    current_claim["body"] = "\n".join(current_lines).strip()
                    parsed_claims.append(current_claim)
                    current_claim = None
                    current_lines = []
                current_section = section_match.group(1).strip()
                if current_section.lower().startswith("agent response"):
                    break
                continue
            if line.strip() == "---":
                if current_claim is not None:
                    current_claim["body"] = "\n".join(current_lines).strip()
                    parsed_claims.append(current_claim)
                    current_claim = None
                    current_lines = []
                continue
            claim_match = re.match(r"^(\d+)\.\s+(.+)", line.strip())
            if claim_match:
                if current_claim is not None:
                    current_claim["body"] = "\n".join(current_lines).strip()
                    parsed_claims.append(current_claim)
                current_claim = {
                    "num": int(claim_match.group(1)),
                    "text": claim_match.group(2),
                    "section": current_section,
                }
                current_lines = [line.strip()]
                continue
            if current_claim is not None:
                current_lines.append(line)

        if current_claim is not None:
            current_claim["body"] = "\n".join(current_lines).strip()
            parsed_claims.append(current_claim)
        return parsed_claims

    def _parse_structured_claims() -> list[dict[str, object]]:
        findings_path = review_dir / "findings.json"
        data = _load_json(findings_path)
        findings = data.get("findings")
        if not isinstance(findings, list):
            return []
        structured_claims: list[dict[str, object]] = []
        for index, finding in enumerate(findings, 1):
            if not isinstance(finding, dict):
                continue
            title = str(finding.get("title", "") or "").strip()
            description = str(finding.get("description", "") or "").strip()
            file_path = str(finding.get("file", "") or "").strip()
            line_number = finding.get("line", 0)
            fix_text = str(finding.get("fix", "") or "").strip()
            body_lines = [
                title,
                f"Description: {description}" if description else "",
                f"File: {file_path}:{line_number}" if file_path and isinstance(line_number, int) and line_number > 0 else (
                    f"File: {file_path}" if file_path else ""
                ),
                f"Fix: {fix_text}" if fix_text else "",
            ]
            structured_claims.append(
                {
                    "num": int(finding.get("id", index) or index),
                    "text": title or description or f"Finding {index}",
                    "section": "Structured Findings",
                    "body": "\n".join(line for line in body_lines if line),
                    "file": file_path,
                    "line": line_number if isinstance(line_number, int) else 0,
                    "description": description,
                    "fix": fix_text,
                }
            )
        return structured_claims

    def _extract_code_anchors(*texts: str) -> list[str]:
        anchors: list[str] = []
        seen: set[str] = set()
        patterns = [
            re.compile(r"`([^`]+)`"),
            re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*\(\))"),
            re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*__[A-Za-z0-9_]+)\b"),
            re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+)\b"),
            re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)\b"),
        ]
        generic = {
            "review", "finding", "findings", "description", "category", "confidence",
            "source", "file", "fix", "error", "warning", "coverage", "json", "path",
            "model", "script", "line", "claim", "claims",
        }
        for text in texts:
            for pattern in patterns:
                for match in pattern.findall(text):
                    anchor = str(match).strip("`").strip()
                    normalized = anchor.replace("()", "")
                    if len(normalized) < 3:
                        continue
                    if normalized.lower() in generic:
                        continue
                    if normalized not in seen:
                        seen.add(normalized)
                        anchors.append(normalized)
        return anchors

    # Extension-swap fallbacks — models frequently hallucinate these when
    # citing data/config files. Order reflects observed frequency: GPT-5.4
    # and Gemini both emit ``.js`` where ``.json`` was meant, and there's
    # a similar ``.yml`` ⇄ ``.yaml`` ambiguity. Known issue logged at
    # /Users/alien/.claude/skills/critique/SKILL.md § Known Issues
    # (2026-04-16 entry).
    _FUZZY_EXT_ALIASES = {
        ".js": (".json",),
        ".jsn": (".json",),
        ".yml": (".yaml",),
        ".yaml": (".yml",),
        ".ts": (".tsx",),
        ".jsx": (".tsx",),
    }

    def _resolve_reference(filepath: str) -> tuple[str, Path | None, str]:
        exact_path = project_dir / filepath
        if exact_path.exists():
            return "exact", exact_path, filepath
        candidates = list(project_dir.rglob(filepath))
        if len(candidates) == 1:
            return "basename", candidates[0], filepath
        if len(candidates) > 1:
            return "ambiguous", None, filepath

        # No direct hit — try extension-swap aliases before declaring missing.
        suffix = Path(filepath).suffix
        for alt_ext in _FUZZY_EXT_ALIASES.get(suffix, ()):
            alt_filepath = filepath[: -len(suffix)] + alt_ext if suffix else filepath + alt_ext
            alt_exact = project_dir / alt_filepath
            if alt_exact.exists():
                return "exact_extswap", alt_exact, alt_filepath
            alt_candidates = list(project_dir.rglob(alt_filepath))
            if len(alt_candidates) == 1:
                return "basename_extswap", alt_candidates[0], alt_filepath

        return "missing", None, filepath

    claims: list[dict[str, object]] = _parse_structured_claims() or _parse_disposition_claims()

    if not claims:
        print("No numbered claims found in disposition.", file=sys.stderr)
        return disposition_path

    # Verify each claim
    verified: list[dict] = []
    for claim in claims:
        claim_text = str(claim["text"])
        body_text = str(claim.get("body", claim_text))
        verdict = "INCONCLUSIVE"
        notes: list[str] = []

        structured_file = str(claim.get("file", "") or "").strip()
        structured_line = int(claim.get("line", 0) or 0)
        file_refs = []
        if structured_file:
            file_refs.append((structured_file, str(structured_line) if structured_line > 0 else ""))
        file_refs.extend(re.findall(
            r"`?([a-zA-Z_][\w/.-]*\.(?:py|js|ts|md|sh|json|yaml|yml|toml|cfg|sql|html|css|clj|cljc|edn))(?::(\d+))?`?",
            body_text,
        ))
        deduped_refs: list[tuple[str, str]] = []
        seen_refs: set[tuple[str, str]] = set()
        for filepath, line_str in file_refs:
            key = (filepath, line_str)
            if key not in seen_refs:
                seen_refs.add(key)
                deduped_refs.append(key)
        file_refs = deduped_refs

        if not file_refs:
            verified.append({**claim, "verdict": verdict, "notes": "no file references or structured file anchors"})
            continue

        claim_anchors = _extract_code_anchors(
            claim_text,
            str(claim.get("description", "") or ""),
            str(claim.get("fix", "") or ""),
            body_text,
        )
        reference_results: list[tuple[str, Path, str]] = []
        for filepath, line_str in file_refs:
            resolution, found_path, display_path = _resolve_reference(filepath)
            if resolution == "missing" or found_path is None:
                verdict = "HALLUCINATED"
                notes.append(f"{filepath} not found")
                reference_results.append((resolution, Path(filepath), line_str))
            elif resolution == "ambiguous":
                notes.append(f"{filepath} matched multiple files")
                reference_results.append((resolution, Path(filepath), line_str))
            else:
                reference_results.append((resolution, found_path, line_str))

        if verdict == "HALLUCINATED":
            verified.append({**claim, "verdict": verdict, "notes": "; ".join(notes)})
            continue

        anchor_confirmed = False
        line_corrected = False
        ambiguous_ref = any(resolution == "ambiguous" for resolution, _, _ in reference_results)
        for resolution, found_path, line_str in reference_results:
            if resolution == "ambiguous":
                continue
            try:
                file_text = found_path.read_text()
                file_lines = file_text.splitlines()
            except OSError:
                notes.append(f"{found_path.relative_to(project_dir)} unreadable")
                continue

            relative_display = str(found_path.relative_to(project_dir))
            if line_str:
                line_num = int(line_str)
                if line_num > len(file_lines):
                    line_corrected = True
                    notes.append(f"{relative_display}:{line_num} beyond EOF ({len(file_lines)} lines)")
                else:
                    start = max(0, line_num - 4)
                    end = min(len(file_lines), line_num + 3)
                    window = "\n".join(file_lines[start:end]).lower()
                    matched = [anchor for anchor in claim_anchors if anchor.lower() in window]
                    if matched:
                        anchor_confirmed = True
                        notes.append(f"{relative_display}:{line_num} anchors {', '.join(sorted(set(matched)))}")
                    else:
                        notes.append(f"{relative_display}:{line_num} readable")
            else:
                file_text_lower = file_text.lower()
                matched = [anchor for anchor in claim_anchors if anchor.lower() in file_text_lower]
                if matched:
                    anchor_confirmed = True
                    notes.append(f"{relative_display} anchors {', '.join(sorted(set(matched)))}")
                else:
                    notes.append(f"{relative_display} exists")

        if anchor_confirmed:
            verdict = "CORRECTED" if line_corrected else "CONFIRMED"
        elif line_corrected:
            verdict = "CORRECTED"
        elif ambiguous_ref:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "INCONCLUSIVE"

        if verdict == "INCONCLUSIVE" and claim_anchors:
            notes.append("anchors not corroborated in resolved file context")

        verified.append({**claim, "verdict": verdict, "notes": "; ".join(notes)})

    # Stats
    confirmed = sum(1 for v in verified if v["verdict"] == "CONFIRMED")
    corrected = sum(1 for v in verified if v["verdict"] == "CORRECTED")
    hallucinated = sum(1 for v in verified if v["verdict"] == "HALLUCINATED")
    inconclusive = sum(1 for v in verified if v["verdict"] == "INCONCLUSIVE")
    verification_summary = {
        "claim_count": len(verified),
        "confirmed_count": confirmed,
        "corrected_count": corrected,
        "hallucinated_count": hallucinated,
        "inconclusive_count": inconclusive,
        "unverifiable_count": inconclusive,
        "hallucination_rate": round(hallucinated / len(verified), 3) if verified else 0.0,
    }

    # Write verified disposition
    out_path = review_dir / "verified-disposition.md"
    lines_out = [
        f"# Verified Disposition — {date.today().isoformat()}\n",
        f"**Claims:** {len(verified)} total — "
        f"{confirmed} CONFIRMED, {corrected} CORRECTED, {hallucinated} HALLUCINATED, {inconclusive} INCONCLUSIVE\n",
    ]
    if hallucinated > 0:
        rate = round(hallucinated / len(verified) * 100)
        lines_out.append(f"**Hallucination rate:** {rate}%\n")
    lines_out.append("")
    lines_out.append("| # | Verdict | Claim | Notes |")
    lines_out.append("|---|---------|-------|-------|")
    for v in verified:
        claim_text = str(v["text"])
        claim_short = claim_text[:80] + ("..." if len(claim_text) > 80 else "")
        lines_out.append(f"| {v['num']} | {v['verdict']} | {claim_short} | {v.get('notes', '')} |")
    lines_out.append("")

    out_path.write_text("\n".join(lines_out) + "\n")
    print(
        f"Verification: {confirmed} confirmed, {corrected} corrected, "
        f"{hallucinated} hallucinated, {inconclusive} inconclusive ({len(verified)} total)",
        file=sys.stderr,
    )
    write_coverage_artifact(
        review_dir,
        verification_summary=verification_summary,
        verified_disposition_path=str(out_path),
    )
    return str(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model-review dispatch: context assembly + parallel llmx + output collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Presets: {', '.join(PRESETS.keys())}. Axes: {', '.join(AXES.keys())}.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--context", type=Path, help="Context file for narrow review")
    group.add_argument(
        "--context-files", nargs="+", metavar="FILE_SPEC",
        help="Auto-assemble context from file:range specs (e.g., plan.md scripts/ir.py:86-110)",
    )
    parser.add_argument("--topic", required=True, help="Short topic label (used in output dir name)")
    parser.add_argument("--project", type=Path, help="Project dir for constitution discovery (default: cwd)")
    parser.add_argument(
        "--axes", default="standard",
        help="Comma-separated axes or preset name (standard, deep, full). Default: standard",
    )
    parser.add_argument("--allow-non-gpt", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--extract",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable extraction. Enabled by default for user-facing reviews; use --no-extract for debugging-only runs.",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After extraction, verify cited files/symbols exist. Implies --extract.",
    )
    parser.add_argument(
        "--questions", type=Path,
        help="JSON file mapping axis names to custom questions (overrides positional question per-axis)",
    )
    parser.add_argument(
        "question", nargs="?",
        default="Review this for logical gaps, missed edge cases, and constitutional alignment.",
        help="Review question for all models",
    )

    args = parser.parse_args()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    # Resolve axes
    try:
        axis_names = resolve_axes(args.axes, allow_non_gpt=bool(args.allow_non_gpt))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.extract and args.verify:
        print("error: --verify cannot be combined with --no-extract", file=sys.stderr)
        return 1

    args.question = _rewrite_underspecified_prompt(args.question, args.topic)

    print(f"Dispatching {len(axis_names)} queries: {', '.join(axis_names)}", file=sys.stderr)

    # Create output directory
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    # Assemble context
    ctx_files = build_context(
        review_dir, project_dir, args.context, axis_names,
        context_file_specs=args.context_files,
    )

    constitution, _ = find_constitution(project_dir)

    # Load per-axis question overrides
    question_overrides = None
    if args.questions:
        if not args.questions.exists():
            print(f"error: questions file {args.questions} not found", file=sys.stderr)
            return 1
        try:
            question_overrides = json.loads(args.questions.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: invalid questions file {args.questions}: {exc}", file=sys.stderr)
            return 1

    # Dispatch and wait
    result = dispatch(review_dir, ctx_files, axis_names, args.question, bool(constitution), question_overrides)
    failures = collect_dispatch_failures(result, ctx_files)
    if failures:
        failure_path = review_dir / "dispatch-failures.json"
        failure_path.write_text(json.dumps({"failures": failures}, indent=2) + "\n")
        result["dispatch_failures"] = str(failure_path)
        result["failed_axes"] = [failure["axis"] for failure in failures]
        print(
            f"error: model-review dispatch produced unusable outputs for "
            f"{', '.join(result['failed_axes'])}; see {failure_path}",
            file=sys.stderr,
        )
        print(json.dumps(result, indent=2))
        return 2

    do_extract = bool(args.extract) or args.verify

    # Optional extraction phase
    if do_extract:
        disposition_path = extract_claims(review_dir, result)
        coverage_path = review_dir / "coverage.json"
        if coverage_path.exists():
            result["coverage"] = str(coverage_path)
            print(f"Coverage written to {coverage_path}", file=sys.stderr)
        if disposition_path:
            result["disposition"] = disposition_path
            print(f"Disposition written to {disposition_path}", file=sys.stderr)

            # Optional verification phase
            if args.verify:
                verified_path = verify_claims(review_dir, disposition_path, project_dir)
                result["verified_disposition"] = verified_path
                print(f"Verified disposition written to {verified_path}", file=sys.stderr)

    print(json.dumps(result, indent=2))

    # Trailing summary — designed to survive `| tail -N` truncation. Callers
    # that pipe this output through tail would otherwise only see closing JSON
    # braces and silently lose the artifact paths and finding counts.
    summary_lines = ["", "=== model-review summary ==="]
    summary_lines.append(f"Review dir:  {review_dir}")
    if result.get("coverage"):
        summary_lines.append(f"Coverage:    {result['coverage']}")
    if result.get("disposition"):
        summary_lines.append(f"Disposition: {result['disposition']}")
    if result.get("verified_disposition"):
        summary_lines.append(f"Verified:    {result['verified_disposition']}")
    try:
        cov_path = result.get("coverage")
        if cov_path:
            cov_data = json.loads(Path(cov_path).read_text())
            ext = cov_data.get("extraction") or {}
            if ext:
                summary_lines.append(
                    f"Findings:    {ext.get('findings_after_dedup', '?')} after dedup, "
                    f"{ext.get('cross_model_agreements', 0)} cross-model"
                )
    except Exception:
        pass
    if result.get("failed_axes"):
        summary_lines.append(f"FAILED axes: {', '.join(result['failed_axes'])}")
    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
