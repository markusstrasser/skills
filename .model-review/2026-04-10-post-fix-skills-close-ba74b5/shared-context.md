# Model Review Context Packet

- Project: `/Users/alien/Projects/skills`
- Axes: `arch,formal`

## Preamble

## DEVELOPMENT CONTEXT

# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler or hacky approaches because they are faster to implement
- Cost-benefit analysis should filter on maintenance burden, supervision cost, complexity budget, and blast radius — not creation effort
- Implementation effort is not a meaningful cost dimension here; only ongoing drag matters

## Context Files

### review/scripts/model-review.py

```text
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

    # Parse claims: numbered lines (e.g., "1. Function X in foo.py has bug")
    claims: list[dict] = []
    current_section = ""
    for line in disposition_text.splitlines():
        section_match = re.match(r"^##\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue
        claim_match = re.match(r"^(\d+)\.\s+(.+)", line.strip())
        if claim_match:
            claims.append({
                "num": int(claim_match.group(1)),
                "text": claim_match.group(2),
                "section": current_section,
            })

    if not claims:
        print("No numbered claims found in disposition.", file=sys.stderr)
        return disposition_path

    # Verify each claim
    verified: list[dict] = []
    for claim in claims:
        text = claim["text"]
        verdict = "UNVERIFIABLE"
        notes: list[str] = []

        # Extract file references: path/file.ext or file.ext:line or `file.ext`
        file_refs = re.findall(
            r"`?([a-zA-Z_][\w/.-]*\.(?:py|js|ts|md|sh|json|yaml|yml|toml|cfg|sql|html|css|clj|cljc|edn))(?::(\d+))?`?",
            text,
        )

        if not file_refs:
            verified.append({**claim, "verdict": verdict, "notes": "no file references"})
            continue

        all_found = True
        for filepath, line_str in file_refs:
            candidates = list(project_dir.rglob(filepath))
            if not candidates:
                verdict = "HALLUCINATED"
                notes.append(f"{filepath} not found")
                all_found = False
            else:
                found_path = candidates[0]
                if line_str:
                    line_num = int(line_str)
                    try:
                        lines = found_path.read_text().splitlines()
                        if line_num > len(lines):
                            notes.append(f"{filepath}:{line_num} beyond EOF ({len(lines)} lines)")
                        else:
                            notes.append(f"{filepath} exists, L{line_num} readable")
                    except Exception:
                        notes.append(f"{filepath} exists but unreadable")
                else:
                    notes.append(f"{filepath} exists")

        if all_found and verdict != "HALLUCINATED":
            verdict = "CONFIRMED"

        verified.append({**claim, "verdict": verdict, "notes": "; ".join(notes)})

    # Stats
    confirmed = sum(1 for v in verified if v["verdict"] == "CONFIRMED")
    hallucinated = sum(1 for v in verified if v["verdict"] == "HALLUCINATED")
    unverifiable = sum(1 for v in verified if v["verdict"] == "UNVERIFIABLE")
    verification_summary = {
        "claim_count": len(verified),
        "confirmed_count": confirmed,
        "hallucinated_count": hallucinated,
        "unverifiable_count": unverifiable,
        "hallucination_rate": round(hallucinated / len(verified), 3) if verified else 0.0,
    }

    # Write verified disposition
    out_path = review_dir / "verified-disposition.md"
    lines_out = [
        f"# Verified Disposition — {date.today().isoformat()}\n",
        f"**Claims:** {len(verified)} total — "
        f"{confirmed} CONFIRMED, {hallucinated} HALLUCINATED, {unverifiable} UNVERIFIABLE\n",
    ]
    if hallucinated > 0:
        rate = round(hallucinated / len(verified) * 100)
        lines_out.append(f"**Hallucination rate:** {rate}%\n")
    lines_out.append("")
    lines_out.append("| # | Verdict | Claim | Notes |")
    lines_out.append("|---|---------|-------|-------|")
    for v in verified:
        claim_short = v["text"][:80] + ("..." if len(v["text"]) > 80 else "")
        lines_out.append(f"| {v['num']} | {v['verdict']} | {claim_short} | {v.get('notes', '')} |")
    lines_out.append("")

    out_path.write_text("\n".join(lines_out) + "\n")
    print(
        f"Verification: {confirmed} confirmed, {hallucinated} hallucinated, "
        f"{unverifiable} unverifiable ({len(verified)} total)",
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### review/scripts/test_model_review.py

```text
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
                "1. `module.py:1` has the wrong value\n"
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
            self.assertEqual(updated["verification"]["hallucinated_count"], 1)
            self.assertEqual(updated["verification"]["unverifiable_count"], 0)
            self.assertEqual(updated["verification"]["hallucination_rate"], 0.5)
            self.assertEqual(Path(updated["artifacts"]["verified_disposition"]).name, "verified-disposition.md")


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
```

### observe/scripts/observe_artifacts.py

```text
#!/usr/bin/env python3
"""Shared paths and JSONL helpers for observe artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path.home() / "Projects" / "meta"
ARTIFACT_SUBDIR = Path("artifacts") / "observe"

MANIFEST_JSON = "manifest.json"
INPUT_MD = "input.md"
CODEX_MD = "codex.md"
COVERAGE_DIGEST_TXT = "coverage-digest.txt"
OPERATIONAL_CONTEXT_TXT = "operational-context.txt"
GEMINI_OUTPUT_MD = "gemini-output.md"
GEMINI_OUTPUT_META_JSON = "gemini-output.meta.json"
GEMINI_OUTPUT_ERROR_JSON = "gemini-output.error.json"
DISPATCH_META_JSON = "dispatch.meta.json"
SIGNALS_JSONL = "signals.jsonl"
CANDIDATES_JSONL = "candidates.jsonl"
PATTERNS_JSONL = "patterns.jsonl"
LAST_SYNTHESIS_MD = "last-synthesis.md"
DIGEST_MD = "digest.md"

OBSERVE_ARTIFACT_ROOT_ENV = "OBSERVE_ARTIFACT_ROOT"
OBSERVE_PROJECT_ROOT_ENV = "OBSERVE_PROJECT_ROOT"


def project_root() -> Path:
    """Resolve the canonical workspace root for observe outputs."""
    env_root = os.environ.get(OBSERVE_PROJECT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()

    env_artifact_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_artifact_root:
        artifact_dir = Path(env_artifact_root).expanduser()
        if len(artifact_dir.parents) >= 2:
            return artifact_dir.parents[1]
        return artifact_dir.parent

    return DEFAULT_PROJECT_ROOT


def artifact_root() -> Path:
    """Resolve the canonical observe artifact directory."""
    env_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()
    return project_root() / ARTIFACT_SUBDIR


def artifact_path(*parts: str) -> Path:
    """Join a path under the canonical artifact root."""
    return artifact_root().joinpath(*parts)


def improvement_log_path() -> Path:
    """Canonical improvement log used by sessions and supervision modes."""
    return project_root() / "improvement-log.md"


def stable_id(prefix: str, *parts: str, length: int = 12) -> str:
    """Create a stable short identifier from a sequence of string parts."""
    digest_input = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha1(digest_input).hexdigest()[:length]
    return f"{prefix}_{digest}"


def jsonl_line(record: dict[str, Any]) -> str:
    """Serialize one JSONL record with stable key ordering."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSONL record, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(jsonl_line(record))
        handle.write("\n")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write a full JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(jsonl_line(record))
            handle.write("\n")
```
