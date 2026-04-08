#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Simple review (1 query: combined)
    model-review.py --context plan.md --topic "config tweak" --axes simple "Review this change"

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

from llmx.api import chat as llmx_chat

# --- Structured output schema (both models return this) ---

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Sequential finding number"},
                    "category": {
                        "type": "string",
                        "enum": ["bug", "logic", "architecture", "missing", "performance", "security", "style", "constitutional"],
                    },
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "title": {"type": "string", "description": "One-line summary"},
                    "description": {"type": "string", "description": "Detailed explanation with evidence"},
                    "file": {"type": "string", "description": "File path if applicable, empty string if architectural"},
                    "line": {"type": "integer", "description": "Line number if applicable, 0 if N/A"},
                    "fix": {"type": "string", "description": "Specific proposed fix"},
                    "confidence": {"type": "number", "description": "0.0-1.0 confidence in this finding"},
                },
                "required": ["id", "category", "severity", "title", "description", "file", "fix", "confidence"],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string", "description": "2-3 sentence overall assessment"},
        "blind_spots": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Where this model is likely wrong",
        },
    },
    "required": ["findings", "summary", "blind_spots"],
    "additionalProperties": False,
}

# --- Axis definitions: model + prompt + api kwargs ---

AXES = {
    "arch": {
        "label": "Gemini (architecture/patterns)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
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
        "model": "gpt-5.4",
        "provider": "openai",
        "api_kwargs": {"timeout": 600, "reasoning_effort": "high", "max_tokens": 32768},
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
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
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
        "model": "gemini-3-flash-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 120},
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
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
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
    "simple": {
        "label": "Gemini Pro (combined review)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
Quick combined review. Be concrete. It is {date}. Budget: ~1000 words.
</system>

{question}

Check for: (1) anything that breaks existing functionality, (2) wrong assumptions, (3) missing edge cases.
If everything looks correct, say so concisely.""",
    },
}

# Presets map a single name to a list of axes
PRESETS = {
    "simple": ["simple"],
    "standard": ["arch", "formal"],
    "deep": ["arch", "formal", "domain", "mechanical"],
    "full": ["arch", "formal", "domain", "mechanical", "alternatives"],
}

GEMINI_PRO_MODEL = "gemini-3.1-pro-preview"
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"
GEMINI_RATE_LIMIT_MARKERS = (
    "503",
    "rate limit",
    "rate-limit",
    "resource_exhausted",
    "overloaded",
    "429",
)


def slugify(text: str, max_len: int = 40) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


def _call_llmx(
    provider: str,
    model: str,
    context_path: Path,
    prompt: str,
    output_path: Path,
    schema: dict | None = None,
    **kwargs,
) -> dict:
    """Call llmx Python API, write output to file, return result dict."""
    context = context_path.read_text()
    full_prompt = context + "\n\n---\n\n" + prompt
    try:
        response = llmx_chat(
            prompt=full_prompt,
            provider=provider,
            model=model,
            temperature=0.7,
            response_format=schema,
            **kwargs,
        )
        output_path.write_text(response.content)
        return {
            "exit_code": 0,
            "size": output_path.stat().st_size,
            "latency": response.latency,
            "error": None,
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
    ctx_files: dict[str, Path],
) -> list[dict[str, object]]:
    """Summarize failed axes for machine-readable failure artifacts."""
    failures: list[dict[str, object]] = []
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}
    for axis, info in dispatch_result.items():
        if axis in skip_keys or not axis_output_failed(info):
            continue
        entry = dict(info)
        entry["axis"] = axis
        entry["context"] = str(ctx_files.get(axis, ""))
        entry["failure_reason"] = (
            "nonzero_exit" if int(entry.get("exit_code", 0)) != 0 else "empty_output"
        )
        failures.append(entry)
    return failures


def is_gemini_rate_limit_failure(model: str, exit_code: int, stderr: str, output_size: int) -> bool:
    if model != GEMINI_PRO_MODEL:
        return False
    if exit_code == 0 and output_size > 0:
        return False
    stderr_lower = stderr.lower()
    return exit_code == 3 or any(marker in stderr_lower for marker in GEMINI_RATE_LIMIT_MARKERS)


def rerun_axis_with_flash(
    axis: str,
    axis_def: dict[str, object],
    review_dir: Path,
    ctx_file: Path,
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
        context_path=ctx_file,
        prompt=prompt,
        output_path=out_path,
        **api_kwargs,
    )


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    """Find constitution text and GOALS.md path in project dir."""
    constitution = ""
    goals_path = None

    # Check .claude/rules/constitution.md first (genomics, projects with standalone file)
    rules_const = project_dir / ".claude" / "rules" / "constitution.md"
    if rules_const.exists():
        constitution = rules_const.read_text().strip()

    # Fall back to CLAUDE.md <constitution> tag or ## Constitution heading
    if not constitution:
        claude_md = project_dir / "CLAUDE.md"
        if claude_md.exists():
            text = claude_md.read_text()
            m = re.search(r"<constitution>(.*?)</constitution>", text, re.DOTALL)
            if m:
                constitution = m.group(1).strip()
            elif "## Constitution" in text:
                idx = text.index("## Constitution")
                rest = text[idx:]
                end = re.search(r"\n## (?!Constitution)", rest)
                constitution = rest[: end.start()].strip() if end else rest.strip()

    for gp in [project_dir / "GOALS.md", project_dir / "docs" / "GOALS.md"]:
        if gp.exists():
            goals_path = str(gp)
            break

    return constitution, goals_path


def parse_file_spec(spec: str) -> str:
    """Parse a file:start-end spec and return the content.

    Formats:
      path/file.py           — entire file
      path/file.py:100-150   — lines 100-150 (1-based, inclusive)
      path/file.py:100       — single line
    """
    if ":" in spec and not spec.startswith("/") or spec.count(":") == 1:
        parts = spec.rsplit(":", 1)
        file_path = parts[0]
        range_spec = parts[1] if len(parts) > 1 else ""
    else:
        file_path = spec
        range_spec = ""

    path = Path(file_path).expanduser()
    if not path.exists():
        return f"# [FILE NOT FOUND: {file_path}]\n"

    text = path.read_text()

    if range_spec and "-" in range_spec:
        try:
            start, end = range_spec.split("-", 1)
            start_line = int(start) - 1  # 0-based
            end_line = int(end)
            lines = text.splitlines()
            text = "\n".join(lines[start_line:end_line])
        except (ValueError, IndexError):
            pass
    elif range_spec:
        try:
            line_no = int(range_spec) - 1
            lines = text.splitlines()
            text = lines[line_no] if 0 <= line_no < len(lines) else text
        except (ValueError, IndexError):
            pass

    return f"# {file_path}" + (f" (lines {range_spec})" if range_spec else "") + f"\n\n{text}\n\n"


def assemble_context_files(specs: list[str]) -> str:
    """Assemble content from multiple file:range specs into one context string."""
    parts = []
    for spec in specs:
        parts.append(parse_file_spec(spec.strip()))
    return "\n".join(parts)


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
    *,
    context_file_specs: list[str] | None = None,
) -> dict[str, Path]:
    """Assemble per-axis context files with constitutional preamble.

    Context sources (in order of precedence):
      1. --context FILE — single pre-assembled context file
      2. --context-files spec1 spec2 ... — auto-assembled from file:range specs
    """
    constitution, goals_path = find_constitution(project_dir)

    preamble = ""
    if constitution:
        # Always include full constitution verbatim — summaries lose nuance
        # that causes reviewers to over-apply or misapply principles
        preamble += "# PROJECT CONSTITUTION (verbatim — review against these, not your priors)\n\n"
        preamble += constitution + "\n\n"
    if goals_path:
        preamble += "# PROJECT GOALS\n\n"
        preamble += Path(goals_path).read_text() + "\n\n"

    # Agent economics framing — always included so reviewers don't
    # recommend trading quality for dev time (which is ~free with agents)
    preamble += "# DEVELOPMENT CONTEXT\n"
    preamble += "All code, plans, and features in this project are developed by AI agents, not human developers. "
    preamble += "Dev creation time is effectively zero. Therefore:\n"
    preamble += "- NEVER recommend trading stability, composability, or robustness for dev time savings\n"
    preamble += "- NEVER recommend simpler/hacky approaches because they're 'faster to implement'\n"
    preamble += "- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort\n"
    preamble += "- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters\n\n"

    # Assemble content from the right source
    if context_file:
        content = context_file.read_text()
    elif context_file_specs:
        content = assemble_context_files(context_file_specs)
    else:
        content = ""

    ctx_files = {}
    for axis in axis_names:
        ctx_path = review_dir / f"{axis}-context.md"
        ctx_path.write_text(preamble + content)
        ctx_files[axis] = ctx_path

    # Warn on size
    for axis, path in ctx_files.items():
        size = path.stat().st_size
        if size > 15_000:
            print(f"warning: {axis} context {size} bytes > 15KB — consider summarizing", file=sys.stderr)

    return ctx_files


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
        out_path = review_dir / f"{axis}-output.md"
        result = _call_llmx(
            provider=str(axis_def["provider"]),
            model=str(axis_def["model"]),
            context_path=ctx_files[axis],
            prompt=prompts[axis],
            output_path=out_path,
            **dict(axis_def.get("api_kwargs") or {}),  # type: ignore[arg-type]
        )
        entry = {
            "label": axis_def["label"],
            "requested_model": str(axis_def["model"]),
            "model": str(axis_def["model"]),
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
            str(axis_def["model"]) == GEMINI_PRO_MODEL
            and result["exit_code"] != 0
            and result.get("error")
            and any(m in result["error"].lower() for m in GEMINI_RATE_LIMIT_MARKERS)
        ):
            entry["fallback_from"] = str(axis_def["model"])
            entry["fallback_reason"] = "gemini_rate_limit"
            entry["initial_exit_code"] = result["exit_code"]
            flash_result = rerun_axis_with_flash(
                axis, axis_def, review_dir, ctx_files[axis], prompts[axis],
            )
            entry["model"] = GEMINI_FLASH_MODEL
            entry["exit_code"] = flash_result["exit_code"]
            entry["size"] = flash_result["size"]

        if entry["size"] == 0:
            entry["failure_reason"] = "empty_output"

        return axis, entry

    # Parallel dispatch via threads
    results: dict = {"review_dir": str(review_dir), "axes": axis_names, "queries": len(axis_names)}
    with ThreadPoolExecutor(max_workers=len(axis_names)) as pool:
        futures = {pool.submit(_run_axis, axis): axis for axis in axis_names}
        for future in as_completed(futures):
            axis, entry = future.result()
            results[axis] = entry

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


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
    """
    extraction_tasks: list[tuple[str, Path, str, str]] = []  # (axis, output_path, model, provider)
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
            extraction_tasks.append((axis, output_path, "gpt-5.3-chat-latest", "openai"))
        else:
            extraction_tasks.append((axis, output_path, "gemini-3-flash-preview", "google"))

    if not extraction_tasks:
        return None

    print(
        f"Extracting claims from {len(extraction_tasks)} outputs...",
        file=sys.stderr,
    )

    def _extract_one(task: tuple[str, Path, str, str]) -> tuple[str, list[dict] | None]:
        axis, output_path, model, provider = task
        extraction_path = review_dir / f"{axis}-extraction.json"
        result = _call_llmx(
            provider=provider,
            model=model,
            context_path=output_path,
            prompt=EXTRACTION_PROMPT,
            output_path=extraction_path,
            schema=FINDING_SCHEMA,
            timeout=120,
        )
        if result["exit_code"] != 0:
            print(f"warning: extraction for {axis} failed: {result.get('error', 'unknown')}", file=sys.stderr)
            return axis, None
        if result["size"] > 0:
            try:
                data = json.loads(extraction_path.read_text())
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
        return None

    # Merge findings across axes — tag source model, cross-reference overlaps
    merged_findings: list[dict] = []
    seen_titles: dict[str, dict] = {}  # title_lower -> finding
    for axis, findings in axis_findings.items():
        source_label = dispatch_result[axis].get("label", axis)
        source_model = dispatch_result[axis].get("model", "unknown")
        for f in findings:
            f["source_axis"] = axis
            f["source_model"] = source_model
            f["source_label"] = source_label
            title_key = f.get("title", "").lower().strip()
            if title_key in seen_titles:
                # Cross-model agreement — boost confidence, tag both sources
                existing = seen_titles[title_key]
                existing.setdefault("also_found_by", []).append(source_label)
                existing["cross_model"] = True
                existing["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.2)
            else:
                seen_titles[title_key] = f
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
        help="Comma-separated axes or preset name (simple, standard, deep, full). Default: standard",
    )
    parser.add_argument(
        "--extract", action="store_true",
        help="After dispatch, auto-extract claims from each output into disposition.md",
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
    if args.axes in PRESETS:
        axis_names = PRESETS[args.axes]
    else:
        axis_names = [a.strip() for a in args.axes.split(",")]
        for a in axis_names:
            if a not in AXES:
                print(f"error: unknown axis '{a}'. Available: {', '.join(AXES.keys())}", file=sys.stderr)
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
        question_overrides = json.loads(args.questions.read_text())

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

    # --verify implies --extract
    do_extract = args.extract or args.verify

    # Optional extraction phase
    if do_extract:
        disposition_path = extract_claims(review_dir, result)
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
