#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Deep review (4 queries: arch + formal + domain + mechanical)
    model-review.py --context plan.md --topic "classification logic" --axes arch,formal,domain,mechanical "Review this"

    # With project dir for goals/governance doc discovery (docs/GOALS.md)
    model-review.py --context plan.md --topic "data wiring" --project ~/Projects/intel "Review this plan"

    # Default: premise scout (cursor-agent, repo workspace) then standard axes
    model-review.py --context plan.md --topic "gateway outbox" --fork "callers exist" --axes standard "Review"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
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
from shared.context_packet import (
    BudgetPolicy,
    ContextPacket,
    FileBlock,
    PacketSection,
    TextBlock,
)
from shared.context_preamble import build_review_preamble_blocks, find_governance
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
                        "enum": [
                            "bug",
                            "logic",
                            "architecture",
                            "missing",
                            "performance",
                            "security",
                            "style",
                            "principles",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "title": {"type": "string", "description": "One-line summary"},
                    "description": {
                        "type": "string",
                        "description": "Detailed explanation with evidence",
                    },
                    "file": {
                        "type": "string",
                        "description": "File path if cited, empty if architectural",
                    },
                    "line": {
                        "type": "integer",
                        "description": "Line number if cited, 0 if N/A",
                    },
                    "fix": {
                        "type": "string",
                        "description": "Proposed fix, empty if unclear",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0.0-1.0 confidence in this finding",
                    },
                },
                "required": [
                    "category",
                    "severity",
                    "title",
                    "description",
                    "file",
                    "line",
                    "fix",
                    "confidence",
                ],
            },
        },
    },
    "required": ["findings"],
}

# --- Axis definitions: model + prompt + api kwargs ---

AXES = {
    "arch": {
        "label": "Gemini A (full review — structure + correctness)",
        "profile": "deep_review",
        "prompt": """\
<system>
Full adversarial review of THIS subpart. Cover architecture AND bugs — not one or the other.
Lens A: structural soundness, coupling, migration posture, what holds up vs what doesn't.
Also flag confirmed/likely bugs and silent-failure paths. It is {date}. Budget: ~1200 words.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Strengths and Weaknesses (structure + correctness)
What holds up and what doesn't. Reference actual code. Include bugs, not just design.

## 2. Better Approaches
Agree (refine) / Disagree (alternative) / Upgrade per recommendation.

## 3. Top 5 Priorities
Ranked with testable verification criteria.

## 4. Goals & Principles Alignment
{principles_instruction}

## 5. Blind Spots In My Own Analysis

## 6. Coverage & assumptions checklist
What was missed? Cross-file drift? Unverified premises (callers exist? join keys on both sides?)?

## 7. Contracts & interfaces (structure view)
API/schema drift, unnamed compatibility boundaries, migration posture.

## 8. Structural assumptions
Load-bearing premises the design depends on. One per line, each starting with "- ".
Examples: callers exist, join keys on both sides, ordering guarantees, schema matches reality.""",
    },
    "gaps": {
        "label": "Gemini B (full review — coverage + assumptions)",
        "profile": "deep_review",
        "prompt": """\
<system>
Second Gemini pass — SAME full mandate (architecture + bugs), different lens.
Lens B: what was missed, cross-file drift, unverified premises. Do NOT only list gaps —
also judge whether the design is sound. It is {date}. Budget: ~1200 words.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. What Was Missed (including bugs the first pass might skip)
Files, line ranges, wiring gaps, logic holes.

## 2. Cross-File Inconsistencies
Same problem solved differently; drift between siblings.

## 3. Unverified Assumptions
Callers exist? Join keys on both sides? Schema matches reality?

## 4. Goals & Principles Alignment
{principles_instruction}

## 5. Blind Spots In My Own Analysis

## 6. Structural assumptions
Load-bearing premises the design depends on. One per line, each starting with "- ".""",
    },
    "correctness": {
        "label": "GPT-5.5 medium A (full review — bugs + structure)",
        "profile": "gpt_general",
        "prompt": """\
<system>
Full adversarial review of THIS subpart. GPT-5.5 medium effort.
Lens A: bugs, boundaries, silent failures — AND whether the architecture supports correctness.
Budget: ~1200 words.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Confirmed or Likely Bugs
file:line | severity | claim | evidence

## 2. Structural Risks to Correctness
Design choices that will breed bugs even if no bug exists yet.

## 3. Boundary / Error-Path Gaps
Unchecked return codes, fail-open paths, missing guards.

## 4. Goals & Principles Alignment
{principles_instruction}

## 5. Where I'm Likely Wrong

## 6. Contract & migration completeness (mechanism view)
Interface breaks, dual paths, orphaned consumers, fail-open error semantics.""",
    },
    "contracts": {
        "label": "GPT-5.5 medium B (full review — migration + interfaces)",
        "profile": "gpt_general",
        "prompt": """\
<system>
Second GPT pass — SAME full mandate (bugs + architecture), different lens.
Lens B: interfaces, contracts, migration completeness — but still flag real bugs you see.
Do NOT defer bugs to the other GPT pass. GPT-5.5 medium. Budget: ~1200 words.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Interface / Contract Breaks
API shape, schema drift, caller obligations.

## 2. Bugs Visible Through a Contract Lens
Integration failures, type mismatches, error-semantics holes.

## 3. Migration & Deletion Completeness
Dual paths, orphaned consumers, unnamed removal conditions.

## 4. Goals & Principles Alignment
{principles_instruction}

## 5. Where I'm Likely Wrong""",
    },
    "formal": {
        "label": "GPT-5.5 high (quantitative/formal — opt-in)",
        "profile": "formal_review",
        "prompt": """\
<system>
You are performing QUANTITATIVE and FORMAL analysis. Other reviewers handle qualitative pattern review. Focus on what they can't do well. Be precise. Show your reasoning. No hand-waving.
Use ONLY when the subpart involves math, proofs, Bayes/stats, or formal invariants. GPT-5.5 at HIGH effort.
Budget: ~1500 words. Tables over prose. Source-grade claims.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Goals & Principles Alignment (Quantified)
{principles_instruction}

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.5) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.""",
    },
    "domain": {
        "label": "Gemini (domain correctness)",
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
        "label": "GPT-5.5 (mechanical audit)",
        "profile": "mechanical_review",
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
        "label": "Gemini (alternative approaches)",
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
    "claude": {
        "label": "Claude Opus 4.8 (third-family adversarial)",
        "profile": "claude_review",
        "prompt": """\
<system>
You are reviewing as an independent third cosigner from a different model family than the other reviewers (Gemini, GPT). Your value is a distinct failure-mode profile — find what they would miss, not what they'd agree on. Be concrete, reference specific code/config/claims. No platitudes. It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Strengths and Weaknesses
What holds up, what doesn't. Reference actual code/config. Be specific about both errors and what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, gaps.

## 3. Better Approaches
For each: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Ranked list of the 5 most impactful changes, each with a testable verification criterion.

## 5. Goals & Principles Alignment
{principles_instruction}

## 6. Blind Spots In My Own Analysis
What am I (Claude) likely getting wrong? Where should you distrust my assessment?""",
    },
    "composer": {
        "label": "Cursor Composer 2.5 (cheap third-lineage adversarial)",
        "profile": "composer_review",
        "prompt": """\
<system>
You are reviewing as an independent cosigner from Cursor's Composer model — a different lineage than the other reviewers (Gemini, GPT, Claude). Your value is a distinct failure-mode profile: find what they would miss. Be concrete, reference specific code/config/claims. No platitudes. COMMIT to verdicts — when you flag a mechanism as a bug, state plainly that it IS a bug; do not hedge it behind "if you meant X". It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Strengths and Weaknesses
What holds up, what doesn't. Reference actual code/config. Be specific about both errors and what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, gaps.

## 3. Better Approaches
For each: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Ranked list of the 5 most impactful changes, each with a testable verification criterion.

## 5. Goals & Principles Alignment
{principles_instruction}

## 6. Blind Spots In My Own Analysis
Where should you distrust my assessment?""",
    },
}

# 2×2 cell metadata: family × lens (inspectable in coverage.json).
AXIS_CELLS: dict[str, dict[str, str]] = {
    "arch": {"family": "gemini", "lens": "structure", "cell": "S_G"},
    "gaps": {"family": "gemini", "lens": "mechanism", "cell": "M_G"},
    "correctness": {"family": "gpt", "lens": "mechanism", "cell": "M_P"},
    "contracts": {"family": "gpt", "lens": "structure", "cell": "S_P"},
}

STRUCTURAL_ASSUMPTIONS_HEADER = re.compile(
    r"^#{2,3}\s*(?:\d+\.\s*)?Structural\s+[Aa]ssumptions\s*:?\s*$",
    re.MULTILINE,
)
CROSS_TALK_INJECTION = """

--- STRUCTURAL ASSUMPTIONS (from structure pass — falsify or confirm each) ---
{assumptions}
--- END STRUCTURAL ASSUMPTIONS ---
Test each assumption against the code. Flag false or unverified assumptions as findings."""


def axis_lens(axis: str) -> str:
    return str(AXIS_CELLS.get(axis, {}).get("lens") or "")


def split_axes_by_lens(axis_names: list[str]) -> tuple[list[str], list[str], list[str]]:
    structure, mechanism, other = [], [], []
    for axis in axis_names:
        lens = axis_lens(axis)
        if lens == "structure":
            structure.append(axis)
        elif lens == "mechanism":
            mechanism.append(axis)
        else:
            other.append(axis)
    return structure, mechanism, other


def parse_structural_assumptions(output_path: Path) -> list[str]:
    """Deterministic parse of ## Structural assumptions bullets from an axis output."""
    if not output_path.is_file():
        return []
    text = output_path.read_text(errors="replace")
    m = STRUCTURAL_ASSUMPTIONS_HEADER.search(text)
    if not m:
        return []
    section = text[m.end() :]
    end = re.search(r"\n##\s*\d", section)
    if end:
        section = section[: end.start()]
    bullets: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            item = re.sub(r"^[-*•]\s*", "", line).strip()
            if len(item) > 8:
                bullets.append(item)
    return bullets[:20]


def format_cross_talk_injection(assumptions: list[str]) -> str:
    if not assumptions:
        return ""
    body = "\n".join(f"- {a}" for a in assumptions)
    return CROSS_TALK_INJECTION.format(assumptions=body)


def collect_structural_assumptions(review_dir: Path, structure_axes: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for axis in structure_axes:
        for item in parse_structural_assumptions(review_dir / f"{axis}-output.md"):
            key = item.lower()
            if key not in seen:
                seen.add(key)
                out.append(item)
    return out


def write_structural_assumptions_artifact(review_dir: Path, assumptions: list[str]) -> Path:
    path = review_dir / "structural-assumptions.json"
    path.write_text(
        json.dumps(
            {"assumptions": assumptions, "count": len(assumptions)},
            indent=2,
        )
        + "\n"
    )
    return path

# Presets map a single name to a list of axes.
# `claude` (Opus 4.8) and `composer` (Cursor Composer 2.5, $0) are opt-in
# third-lineage cosigners — intentionally NOT in any preset. Request explicitly:
# `--axes arch,formal,claude` or `--axes arch,formal,composer`.
#
# cross2/lens2 = diagonal 2×2 (S_G + M_P). cross4/lens4/standard = full grid.
# model-review CLI default stays `standard` until evals/critique_replay/ROUTING_VERDICT.md
# promotes cross2 (see review_gate triage `preset` field).
PRESETS = {
    # Legacy default: 2× Gemini + 2× GPT-medium (4 lenses).
    "standard": ["arch", "gaps", "correctness", "contracts"],
    # Diagonal cross-lab: Gemini structure + GPT mechanism (folded checklists in arch/correctness).
    "cross2": ["arch", "correctness"],
    "lens2": ["arch", "correctness"],
    # Full 2×2 grid (4 cells).
    "cross4": ["arch", "gaps", "correctness", "contracts"],
    "lens4": ["arch", "gaps", "correctness", "contracts"],
    # Math/formal-dense reviews: add `formal` explicitly, e.g. --axes standard,formal
    "deep": ["arch", "gaps", "correctness", "contracts", "domain", "mechanical"],
    "full": ["arch", "gaps", "correctness", "contracts", "domain", "mechanical", "alternatives"],
}

# Premise scout runs before packet-only axes (VOI-sequenced review ADR).
PREMISE_SCOUT_TIMEOUT = 90
PREMISE_SCOUT_CONTEXT_CAP = 120_000  # chars of packet fed to scout stdin

PREMISE_SCOUT_PROMPT = """\
VOI premise scout — falsify load-bearing premises BEFORE adversarial review.

You have read-only access to the repo workspace. The design packet is below.

Rules:
- Do NOT critique aesthetics or propose redesigns — only verify/falsify premises.
- List 3–5 load-bearing premises (callers exist? paths real? join keys on both sides? cited helpers exist?).
- For each premise: run deterministic checks that finish in <60s (grep, read cited files, git log -5 -- path).
- Probes ≥60s or needing API: disposition "proposed" only — do not run them.
- One fork focus: {fork}

Review question: {question}

Respond in markdown with:
## Premises checked
## Executed probes (<60s)
## Proposed probes (not run)
## conviction_after (high|medium|low)
## recommendation (proceed | human checkpoint)

End with a fenced JSON block (voi-scout.json shape):
```json
{{
  "fork": "...",
  "uncertainty": "...",
  "voi_actions": [{{"action": "...", "cost_sec": 5, "disposition": "executed|proposed", "result": "..."}}],
  "conviction_after": "high|medium|low",
  "recommendation": "proceed | escalate cross4 | human checkpoint"
}}
```

--- DESIGN PACKET ---
{packet}
"""

PARALLEL_DISPATCH_WAIT_DEFAULT = 720.0
DISPATCH_SCHEMA_VERSION = "dispatch.v1"
EXECUTION_RECEIPT_SCHEMA_VERSION = "execution-receipt.v1"
SUPPORTED_DISPATCH_SCHEMAS = frozenset({DISPATCH_SCHEMA_VERSION})


class DispatchBudget:
    """Orchestrator wall-clock cap — skip axes that cannot finish; never truncate timeouts."""

    __slots__ = ("deadline_mono",)

    def __init__(self, deadline_mono: float | None = None) -> None:
        self.deadline_mono = deadline_mono

    @classmethod
    def from_seconds(cls, seconds: int | None) -> "DispatchBudget":
        if seconds is None or seconds <= 0:
            return cls(deadline_mono=None)
        return cls(deadline_mono=time.monotonic() + seconds)

    @property
    def active(self) -> bool:
        return self.deadline_mono is not None

    def remaining(self) -> float | None:
        if self.deadline_mono is None:
            return None
        return max(0.0, self.deadline_mono - time.monotonic())

    def can_start(self, profile_timeout: int) -> bool:
        """Start only if the full profile timeout fits in remaining budget."""
        rem = self.remaining()
        if rem is None:
            return True
        return rem >= profile_timeout

    def wait_timeout(self, default: float = PARALLEL_DISPATCH_WAIT_DEFAULT) -> float:
        rem = self.remaining()
        if rem is None:
            return default
        return max(1.0, min(default, rem))


def _resolved_axis_timeout(axis: str) -> int:
    """Wall-clock timeout for budget gate — mirrors llmx high/xhigh auto-scale."""
    profile_name = str(AXES[axis]["profile"])
    profile_def = dispatch_core.PROFILES[profile_name]
    timeout = int(profile_def.timeout)
    effort = (profile_def.reasoning_effort or "").lower()
    scaled = {"high": 600, "xhigh": 1200}.get(effort)
    if scaled and scaled > timeout:
        timeout = scaled
    return timeout


def _axis_profile_timeout(axis: str) -> int:
    return _resolved_axis_timeout(axis)


def _budget_skipped_axis(
    axis: str, review_dir: Path, budget: DispatchBudget, profile_timeout: int
) -> dict:
    axis_def = AXES[axis]
    profile_def = dispatch_core.PROFILES[str(axis_def["profile"])]
    rem = budget.remaining()
    return {
        "label": axis_def["label"],
        "requested_model": profile_def.model,
        "model": profile_def.model,
        "exit_code": 1,
        "output": str(review_dir / f"{axis}-output.md"),
        "size": 0,
        "failure_reason": "budget_exhausted",
        "budget_remaining_seconds": round(rem, 1) if rem is not None else None,
        "profile_timeout": profile_timeout,
    }


def load_dispatch_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def validate_dispatch_schema(manifest: dict) -> str | None:
    version = manifest.get("schema_version")
    if version is None:
        return None
    if version not in SUPPORTED_DISPATCH_SCHEMAS:
        return f"unsupported dispatch schema_version {version!r}"
    return None


def dispatch_manifest_blockers(manifest: dict) -> list[str]:
    return [str(b) for b in (manifest.get("blockers") or []) if str(b).strip()]


def _axis_execution_status(entry: dict) -> str:
    reason = entry.get("failure_reason")
    if reason == "budget_exhausted":
        return "skipped_budget"
    if reason == "thread_timeout":
        return "thread_timeout"
    if int(entry.get("exit_code", 0)) != 0 or int(entry.get("size", 0)) == 0:
        return str(reason) if reason else "failed"
    return "completed"


def _execution_overall(axis_statuses: dict[str, dict]) -> str:
    statuses = [info["status"] for info in axis_statuses.values()]
    if not statuses:
        return "failed"
    if all(s == "completed" for s in statuses):
        return "complete"
    if all(s == "skipped_budget" for s in statuses):
        return "incomplete_all_skipped"
    if any(s == "completed" for s in statuses):
        return "partial"
    return "failed"


def write_execution_receipt(
    review_dir: Path,
    *,
    axis_names: list[str],
    dispatch_result: dict,
    effective_policy: dict,
) -> Path:
    axes_out: dict[str, dict] = {}
    for axis in axis_names:
        entry = dispatch_result.get(axis)
        if not isinstance(entry, dict):
            axes_out[axis] = {"status": "missing"}
            continue
        axes_out[axis] = {
            "status": _axis_execution_status(entry),
            "model": entry.get("model"),
            "failure_reason": entry.get("failure_reason"),
            "budget_remaining_seconds": entry.get("budget_remaining_seconds"),
            "profile_timeout": entry.get("profile_timeout"),
        }
    receipt = {
        "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
        "overall": _execution_overall(axes_out),
        "effective_policy": effective_policy,
        "axes": axes_out,
        "elapsed_seconds": dispatch_result.get("elapsed_seconds"),
    }
    path = review_dir / "execution-receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    return path


def apply_dispatch_manifest(args: argparse.Namespace, manifest_path: Path) -> dict:
    """Merge dispatch_policy from triage; CLI flags already set win over manifest."""
    manifest = load_dispatch_manifest(manifest_path)
    policy = manifest.get("dispatch_policy") or {}
    if args.scout is None:
        args.scout = bool(policy.get("premise_scout", True))
    if args.context_scope is None:
        args.context_scope = policy.get("context_scope") or "repo"
    if args.budget_seconds is None:
        args.budget_seconds = policy.get("budget_seconds")
    if not args.irreversible and policy.get("irreversible"):
        args.irreversible = True
    if not args.cross_talk and policy.get("cross_talk"):
        args.cross_talk = True
    if args.axes is None:
        design = (manifest.get("layers") or {}).get("design") or {}
        args.axes = str(design.get("axes") or manifest.get("preset") or "standard")
    return manifest


def build_effective_policy(args: argparse.Namespace) -> dict:
    return {
        "scout": bool(args.scout),
        "context_scope": args.context_scope,
        "budget_seconds": args.budget_seconds,
        "axes": args.axes,
        "irreversible": bool(args.irreversible),
        "cross_talk": bool(args.cross_talk),
        "extract": bool(args.extract),
        "verify": bool(args.verify),
    }

# Primary Gemini critique axis (deep_review = gemini-3.5-flash since 2026-05-24).
GEMINI_PRIMARY_MODEL = dispatch_core.PROFILES["deep_review"].model
# Rate-limit fallback target for the Gemini (arch) axis. When gemini-3.5-flash
# rate-limits, retry the axis on gpt-5.5 — the rule-sanctioned move ("after a
# Gemini rate-limit, switch to GPT or Flash"; llmx transport-routing) and an
# adversarial-grade model. Tradeoff: this collapses the arch+formal pair to GPT
# for that one review (degraded cross-model diversity), accepted because it is
# rare and beats the alternatives — gemini-3.1-pro-preview was RETIRED from
# automation 2026-06-07 (same-provider, so it shares 3.5-flash's outage, and is
# the ~25%-hallucination runner-up); gemini-3-flash-preview is the cheap
# classification slot (~42% hallucination on critique work, per-model
# disposition audit 2026-06-01). A Claude model is deliberately NOT used: the
# author under review is Claude, so a Claude fallback would reintroduce the
# same-model martingale this skill exists to avoid. 3.1-pro stays available for
# explicit manual use via the legacy_pro_review profile (its ARC-AGI-2 / GPQA /
# video niches) — it just never auto-fires now.
GEMINI_FALLBACK_MODEL = dispatch_core.PROFILES["gpt_general"].model
COVERAGE_SCHEMA_VERSION = "review-coverage.v1"
# Cross-model dedup threshold (keyword-set Jaccard). Lowered 0.3 -> 0.25 on
# 2026-06-01: at 0.3 only 0.9% of GPT findings matched a Gemini finding, and a
# manual eyeball of the 0.25-0.3 band showed it was full of genuine same-issue
# pairs worded differently ("Invalid Wilson intervals on dependent splits" vs
# "Wilson intervals too narrow if holdout folds are correlated"). 0.25 ~triples
# recovered agreements (0.9%->2.5%); going to 0.2 adds recall but more borderline
# merges. Same-file overlap is NOT used as a merge signal — 99% of same-file
# cross-axis pairs are different problems in a shared file (dedup_probe, 2026-06-01).
CROSS_MODEL_JACCARD_THRESHOLD = 0.25
GEMINI_RATE_LIMIT_MARKERS = (
    "503",
    "unavailable",  # Flex-tier load-shed can surface as bare "UNAVAILABLE"
    "rate limit",
    "rate-limit",
    "resource_exhausted",
    "overloaded",
    "429",
)
# GPT API-key path can hit billing exhaustion / quota while the ChatGPT
# subscription (codex-cli, $0) works fine (see ~/.claude/rules/llmx-routing.md).
# On these, fall back to the subscription transport so a paid-API outage never
# silently degrades a review to single-model. Fires ONLY on failure.
GPT_QUOTA_MARKERS = (
    "insufficient_quota",
    "quota",
    "billing",
    "credit",
    "payment required",
    "exhausted balance",
    "429",
    "rate limit",
    "rate-limit",
)


class ContextArtifact(NamedTuple):
    content_path: Path
    manifest_path: Path


class PremiseScoutResult(NamedTuple):
    skipped: bool
    skip_reason: str | None
    markdown_path: Path | None
    json_path: Path | None
    conviction: str | None


def _resolve_cursor_agent_bin() -> str | None:
    for name in ("cursor-agent", "agent"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _extract_json_block(text: str) -> dict | None:
    for match in re.finditer(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE):
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
    return None


def _scout_skip_payload(
    *,
    fork: str | None,
    topic: str,
    skip_reason: str,
) -> dict:
    """Skip is NOT low conviction — absence of scout ≠ substantive verdict."""
    return {
        "fork": fork or topic,
        "skipped": True,
        "skip_reason": skip_reason,
        "conviction_after": None,
        "recommendation": "proceed",
    }


def check_scout_conviction_gate(
    scout_result: PremiseScoutResult | None,
    *,
    irreversible: bool,
    force: bool,
) -> int | None:
    """ADR gate: block adjudication only on executed scout + low + irreversible."""
    if force or scout_result is None or scout_result.skipped:
        return None
    if not irreversible:
        return None
    conviction = (scout_result.conviction or "").strip().lower()
    if conviction == "low":
        print(
            "error: premise scout conviction=low on --irreversible review; "
            "human checkpoint required (or pass --force-scout to proceed anyway)",
            file=sys.stderr,
        )
        return 3
    return None


def should_run_premise_scout(
    *,
    scout: bool,
    context_scope: str,
    has_context: bool,
) -> bool:
    return scout and context_scope == "repo" and has_context


def run_premise_scout(
    *,
    review_dir: Path,
    project_dir: Path,
    context_path: Path,
    topic: str,
    question: str,
    fork: str | None = None,
    timeout: int = PREMISE_SCOUT_TIMEOUT,
    budget: DispatchBudget | None = None,
) -> PremiseScoutResult:
    """Repo-grounded premise falsifier via cursor-agent (Composer 2.5, workspace=project)."""
    scout_profile = dispatch_core.PROFILES["premise_scout"]
    scout_model = scout_profile.model
    effective_timeout = timeout
    if budget is not None:
        if not budget.can_start(timeout):
            reason = (
                f"budget exhausted ({budget.remaining():.0f}s left, "
                f"scout needs {timeout}s)"
            )
            payload = _scout_skip_payload(fork=fork, topic=topic, skip_reason=reason)
            json_path = review_dir / "voi-scout.json"
            json_path.write_text(json.dumps(payload, indent=2) + "\n")
            return PremiseScoutResult(True, payload["skip_reason"], None, json_path, None)
    bin_path = _resolve_cursor_agent_bin()
    md_path = review_dir / "premise-scout.md"
    json_path = review_dir / "voi-scout.json"
    if not bin_path:
        payload = _scout_skip_payload(
            fork=fork, topic=topic, skip_reason="cursor-agent not installed"
        )
        json_path.write_text(json.dumps(payload, indent=2) + "\n")
        return PremiseScoutResult(True, payload["skip_reason"], None, json_path, None)

    packet = context_path.read_text(errors="replace")
    if len(packet) > PREMISE_SCOUT_CONTEXT_CAP:
        packet = packet[:PREMISE_SCOUT_CONTEXT_CAP] + "\n\n[... packet truncated for scout ...]"

    prompt = PREMISE_SCOUT_PROMPT.format(
        fork=fork or topic,
        question=question,
        packet=packet,
    )
    cmd = [
        bin_path,
        "-p",
        "--mode",
        "ask",
        "--trust",
        "--model",
        scout_model,
        "--workspace",
        str(project_dir.resolve()),
        "--output-format",
        "text",
    ]
    print(
        f"[premise-scout] cursor-agent workspace={project_dir} fork={fork or topic!r}",
        file=sys.stderr,
    )
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            cwd=str(project_dir),
        )
    except subprocess.TimeoutExpired:
        payload = _scout_skip_payload(
            fork=fork, topic=topic, skip_reason=f"timeout after {effective_timeout}s"
        )
        json_path.write_text(json.dumps(payload, indent=2) + "\n")
        return PremiseScoutResult(True, payload["skip_reason"], None, json_path, None)

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0 or not stdout:
        reason = stderr[:500] or f"exit {proc.returncode}"
        payload = _scout_skip_payload(fork=fork, topic=topic, skip_reason=reason)
        json_path.write_text(json.dumps(payload, indent=2) + "\n")
        return PremiseScoutResult(True, reason, None, json_path, None)

    md_path.write_text(stdout + "\n")
    parsed = _extract_json_block(stdout)
    if parsed is None:
        parsed = {
            "fork": fork or topic,
            "uncertainty": question,
            "voi_actions": [],
            "conviction_after": "unknown",
            "recommendation": "proceed",
            "parse_warning": "no json fence in scout output",
        }
    parsed.setdefault("fork", fork or topic)
    parsed["skipped"] = False
    json_path.write_text(json.dumps(parsed, indent=2) + "\n")
    conviction = str(parsed.get("conviction_after") or "unknown")
    return PremiseScoutResult(False, None, md_path, json_path, conviction)


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
        raise ValueError(
            "the `simple` preset was removed; use `standard` for the GPT-inclusive default"
        )

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

    if not allow_non_gpt and not any(
        axis_uses_gpt(axis_name) for axis_name in axis_names
    ):
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
    "close",
    "review",
    "verify",
    "check",
    "model",
    "deep",
    "full",
    "standard",
    "model-review",
    "critique",
    "audit",
    "fix",
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
        overrides = (
            dispatch_core.DispatchOverrides(**override_payload)
            if override_payload
            else None
        )
        result = dispatch_core.dispatch(
            profile=profile,
            prompt=prompt,
            context_path=context_path,
            context_manifest_path=context_manifest_path,
            output_path=output_path,
            schema=schema,
            overrides=overrides,
            # Transport is owned by the profile (auth on DispatchProfile).
            # Do NOT pass api_only here — a hardcode re-states/overrides the
            # profile and silently breaks CLI-transport profiles (composer_review
            # → cursor → was routed to the OpenAI API → 404). The dispatch default
            # (None) resolves to each profile's declared transport.
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
        entry["context"] = (
            str(context_content_path(ctx_files[axis])) if axis in ctx_files else ""
        )
        entry["failure_reason"] = (
            "nonzero_exit" if int(entry.get("exit_code", 0)) != 0 else "empty_output"
        )
        failures.append(entry)
    return failures


def rerun_axis_with_fallback(
    axis: str,
    axis_def: dict[str, object],
    review_dir: Path,
    ctx_file: Path | ContextArtifact,
    prompt: str,
    budget: DispatchBudget | None = None,
) -> dict:
    """Retry the rate-limited primary Gemini (arch) axis on the cross-provider
    adversarial fallback (gpt-5.5 since 2026-06-07; 3.1-pro retired from
    automation). Collapses the pair to GPT for this review, but rare + reliable."""
    out_path = review_dir / f"{axis}-output.md"
    print(
        f"warning: {axis} hit Gemini rate limits; retrying once on the "
        f"cross-provider fallback ({GEMINI_FALLBACK_MODEL})",
        file=sys.stderr,
    )
    api_kwargs = dict(axis_def.get("api_kwargs") or {})  # type: ignore[arg-type]
    profile_timeout = _axis_profile_timeout(axis)
    if budget is not None and not budget.can_start(profile_timeout):
        return {
            "exit_code": 1,
            "size": 0,
            "latency": 0,
            "error": "budget exhausted before fallback retry",
        }
    return _call_llmx(
        provider="google",
        model=GEMINI_FALLBACK_MODEL,
        context_path=context_content_path(ctx_file),
        context_manifest_path=context_manifest_path(ctx_file),
        prompt=prompt,
        output_path=out_path,
        **api_kwargs,
    )


def rerun_gpt_axis_via_subscription(
    axis: str,
    model: str,
    review_dir: Path,
    ctx_file: Path | ContextArtifact,
    prompt: str,
    budget: DispatchBudget | None = None,
) -> dict:
    """Retry a GPT axis that hit API billing/quota via the ChatGPT SUBSCRIPTION
    transport (llmx CLI `--subscription` -> codex-cli, $0). The default dispatch uses
    api_only=True (metered API); when that path is billing-exhausted, the paid-API
    outage would otherwise silently degrade the review to single-model. Subprocess
    (not the in-process llmx.api) because subscription routing is CLI-only. Fires only
    on failure; bounded by a timeout — if it also fails we are no worse off."""
    import subprocess

    out_path = review_dir / f"{axis}-output.md"
    print(
        f"warning: {axis} GPT API billing/quota failure; retrying once via ChatGPT "
        f"subscription (llmx --subscription, $0)",
        file=sys.stderr,
    )
    cmd = [
        "llmx",
        "chat",
        "-m",
        model,
        "--subscription",
        "-e",
        "high",
        "-f",
        str(context_content_path(ctx_file)),
        "-o",
        str(out_path),
        prompt,
    ]
    sub_timeout = 660
    if budget is not None:
        if not budget.can_start(sub_timeout):
            return {
                "exit_code": 1,
                "size": 0,
                "latency": 0,
                "error": "budget exhausted before subscription retry",
            }
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=sub_timeout)
        size = out_path.stat().st_size if out_path.exists() else 0
        ok = r.returncode == 0 and size > 0
        return {
            "exit_code": 0 if ok else 1,
            "size": size,
            "latency": 0,
            "error": None
            if ok
            else (r.stderr or "subscription retry produced no output")[:500],
        }
    except Exception as e:  # noqa: BLE001 — fallback must never raise into the axis loop
        return {
            "exit_code": 1,
            "size": 0,
            "latency": 0,
            "error": f"subscription retry failed: {str(e)[:300]}",
        }


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
    *,
    context_file_specs: list[str] | None = None,
    budget_limit_override: int | None = None,
    premise_scout_path: Path | None = None,
) -> dict[str, ContextArtifact]:
    """Assemble shared context packet with goals/governance preamble.

    Context sources (additive, both may be supplied; at least one required):
      1. --context FILE — pre-assembled context file (high priority, narrative)
      2. --context-files spec1 spec2 ... — file:range excerpts (lower priority, auxiliary)

    When both are supplied, --context becomes the "Provided Context" section and
    --context-files become an additional "Context Files" section. Mutex relaxed 2026-05-07.
    """
    preamble_blocks, _ = build_review_preamble_blocks(project_dir)
    packet_sections = [PacketSection("Preamble", preamble_blocks)]

    if premise_scout_path and premise_scout_path.exists():
        packet_sections.append(
            PacketSection(
                "Premise Scout (repo-grounded)",
                [
                    TextBlock(
                        str(premise_scout_path),
                        premise_scout_path.read_text(),
                        priority=350,
                        drop_if_needed=False,
                        metadata={"path": str(premise_scout_path), "role": "premise_scout"},
                    )
                ],
            )
        )

    if context_file:
        packet_sections.append(
            PacketSection(
                "Provided Context",
                [
                    TextBlock(
                        str(context_file),
                        context_file.read_text(),
                        priority=400,
                        drop_if_needed=False,
                        metadata={"path": str(context_file)},
                    )
                ],
            )
        )
    if context_file_specs:
        file_blocks = []
        for spec_text in context_file_specs:
            spec = parse_file_spec(spec_text.strip())
            excerpt, truncated, omission_reason = read_file_excerpt(
                spec, max_chars=None
            )
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
    if not context_file and not context_file_specs:
        packet_sections.append(
            PacketSection(
                "Provided Context",
                [TextBlock("Context", "", priority=10, drop_if_needed=True)],
            )
        )

    token_limits = [
        dispatch_core.profile_input_budget(AXES[axis]["profile"])["input_token_limit"]
        for axis in axis_names
        if dispatch_core.profile_input_budget(AXES[axis]["profile"])[
            "input_token_limit"
        ]
        is not None
    ]
    budget_limit = (
        budget_limit_override
        if budget_limit_override is not None
        else (min(token_limits) if token_limits else 120000)
    )
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
    return {
        axis: ContextArtifact(content_path=content_path, manifest_path=manifest_path)
        for axis in axis_names
    }


def dispatch(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_governance: bool,
    question_overrides: dict[str, str] | None = None,
    budget: DispatchBudget | None = None,
) -> dict:
    """Fire N llmx API calls in parallel (one per axis), wait, return results."""
    today = date.today().isoformat()

    principles_instruction = {
        "arch": (
            "Where does the reviewed work violate or neglect the project's stated goals and operating principles? Which principles are well-served?"
            if has_governance
            else "No project goals/governance provided — assess internal consistency only."
        ),
        "formal": (
            "For each stated operating principle: coverage score (0-100%), specific gaps, suggested fixes."
            if has_governance
            else "No project goals/governance provided — assess internal logical consistency."
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
            principles_instruction=principles_instruction.get(axis, ""),
        )

    def _run_axis(axis: str) -> tuple[str, dict]:
        axis_def = AXES[axis]
        profile_name = str(axis_def["profile"])
        profile_def = dispatch_core.PROFILES[profile_name]
        profile_timeout = profile_def.timeout
        out_path = review_dir / f"{axis}-output.md"
        if budget is not None and not budget.can_start(profile_timeout):
            return axis, _budget_skipped_axis(axis, review_dir, budget, profile_timeout)
        context_artifact = ctx_files[axis]
        result = _call_llmx(
            provider=profile_def.provider,
            model=profile_def.model,
            context_path=context_content_path(context_artifact),
            context_manifest_path=context_manifest_path(context_artifact),
            prompt=prompts[axis],
            output_path=out_path,
            timeout=profile_timeout,
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

        # Primary Gemini axis rate-limited -> retry once with the runner-up
        # critique model (3.1-Pro), not the cheap classification model.
        if (
            profile_def.model == GEMINI_PRIMARY_MODEL
            and result["exit_code"] != 0
            and result.get("error")
            and any(m in result["error"].lower() for m in GEMINI_RATE_LIMIT_MARKERS)
        ):
            entry["fallback_from"] = profile_def.model
            entry["fallback_reason"] = "gemini_rate_limit"
            entry["initial_exit_code"] = result["exit_code"]
            fallback_result = rerun_axis_with_fallback(
                axis,
                axis_def,
                review_dir,
                ctx_files[axis],
                prompts[axis],
                budget=budget,
            )
            entry["model"] = GEMINI_FALLBACK_MODEL
            entry["exit_code"] = fallback_result["exit_code"]
            entry["size"] = fallback_result["size"]
            if fallback_result.get("latency"):
                entry["latency"] = fallback_result["latency"]
            entry.pop("stderr", None)
            if fallback_result.get("error"):
                entry["stderr"] = fallback_result["error"]

        # GPT API billing/quota fallback to ChatGPT subscription (codex-cli, $0).
        # Mirrors the Gemini-Pro->Flash fallback above; fires only on failure so the
        # common path is untouched. Prevents a paid-API outage from silently
        # degrading a touches-everything review to single-model (happened 2026-05-31).
        elif (
            profile_def.provider == "openai"
            and result["exit_code"] != 0
            and result.get("error")
            and any(m in result["error"].lower() for m in GPT_QUOTA_MARKERS)
        ):
            entry["fallback_from"] = profile_def.model
            entry["fallback_reason"] = "gpt_api_quota"
            entry["initial_exit_code"] = result["exit_code"]
            sub_result = rerun_gpt_axis_via_subscription(
                axis,
                profile_def.model,
                review_dir,
                ctx_files[axis],
                prompts[axis],
                budget=budget,
            )
            entry["model"] = f"{profile_def.model} (subscription)"
            entry["exit_code"] = sub_result["exit_code"]
            entry["size"] = sub_result["size"]
            entry.pop("stderr", None)
            if sub_result.get("error"):
                entry["stderr"] = sub_result["error"]

        if entry["size"] == 0:
            entry["failure_reason"] = "empty_output"

        return axis, entry

    # Parallel dispatch via threads
    results: dict = {
        "review_dir": str(review_dir),
        "axes": axis_names,
        "queries": len(axis_names),
    }
    wait_timeout = (
        budget.wait_timeout() if budget is not None else PARALLEL_DISPATCH_WAIT_DEFAULT
    )
    with ThreadPoolExecutor(max_workers=len(axis_names)) as pool:
        futures = {pool.submit(_run_axis, axis): axis for axis in axis_names}
        try:
            for future in as_completed(futures, timeout=wait_timeout):
                axis, entry = future.result()
                results[axis] = entry
        except TimeoutError:
            # as_completed raises at iterator level when global timeout expires
            for future, axis in futures.items():
                if axis not in results:
                    results[axis] = {
                        "label": AXES[axis]["label"],
                        "requested_model": dispatch_core.PROFILES[
                            str(AXES[axis]["profile"])
                        ].model,
                        "model": dispatch_core.PROFILES[
                            str(AXES[axis]["profile"])
                        ].model,
                        "exit_code": 1,
                        "output": str(review_dir / f"{axis}-output.md"),
                        "size": 0,
                        "failure_reason": "thread_timeout",
                    }

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


def dispatch_cross_talk(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_governance: bool,
    question_overrides: dict[str, str] | None = None,
    budget: DispatchBudget | None = None,
) -> dict:
    """Sequential cross-talk: structure lenses first, then mechanism with injected assumptions."""
    structure_axes, mechanism_axes, other_axes = split_axes_by_lens(axis_names)
    if not structure_axes or not mechanism_axes:
        return dispatch(
            review_dir,
            ctx_files,
            axis_names,
            question,
            has_governance,
            question_overrides,
            budget=budget,
        )

    t0 = time.time()
    results: dict = {
        "review_dir": str(review_dir),
        "axes": axis_names,
        "queries": len(axis_names),
        "cross_talk": True,
    }
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds", "cross_talk"}

    struct_result = dispatch(
        review_dir,
        ctx_files,
        structure_axes,
        question,
        has_governance,
        question_overrides,
        budget=budget,
    )
    for key, val in struct_result.items():
        if key not in skip_keys:
            results[key] = val

    assumptions = collect_structural_assumptions(review_dir, structure_axes)
    assumptions_path = write_structural_assumptions_artifact(review_dir, assumptions)
    results["structural_assumptions"] = str(assumptions_path)
    if assumptions:
        print(
            f"Cross-talk: {len(assumptions)} structural assumptions → mechanism passes",
            file=sys.stderr,
        )
    else:
        results["cross_talk_degraded"] = True
        print(
            "warning: --cross-talk enabled but no structural assumptions parsed; "
            "mechanism passes run without injected context (cross_talk_degraded=true)",
            file=sys.stderr,
        )

    injection = format_cross_talk_injection(assumptions)
    mech_overrides = dict(question_overrides or {})
    for axis in mechanism_axes:
        base = mech_overrides.get(axis, question)
        mech_overrides[axis] = base + injection

    if mechanism_axes:
        if budget is not None and not any(
            budget.can_start(_axis_profile_timeout(axis)) for axis in mechanism_axes
        ):
            print(
                "warning: dispatch budget exhausted before mechanism cross-talk phase; "
                "skipping mechanism axes",
                file=sys.stderr,
            )
            for axis in mechanism_axes:
                results[axis] = _budget_skipped_axis(
                    axis,
                    review_dir,
                    budget,
                    _axis_profile_timeout(axis),
                )
        else:
            mech_result = dispatch(
                review_dir,
                ctx_files,
                mechanism_axes,
                question,
                has_governance,
                mech_overrides,
                budget=budget,
            )
            for key, val in mech_result.items():
                if key not in skip_keys:
                    results[key] = val

    if other_axes:
        other_result = dispatch(
            review_dir,
            ctx_files,
            other_axes,
            question,
            has_governance,
            question_overrides,
            budget=budget,
        )
        for key, val in other_result.items():
            if key not in skip_keys:
                results[key] = val

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
            str(axis)
            for axis in dispatch_result.get("axes", [])
            if isinstance(axis, str)
        ]
        if not requested_axes:
            requested_axes = [
                axis
                for axis, info in dispatch_result.items()
                if axis
                not in {
                    "review_dir",
                    "axes",
                    "queries",
                    "elapsed_seconds",
                    "dispatch_failures",
                    "failed_axes",
                }
                and isinstance(info, dict)
            ]
        dispatch_axes = [
            {
                "axis": axis,
                "label": info.get("label"),
                "cell": (AXIS_CELLS.get(axis) or {}).get("cell"),
                "family": (AXIS_CELLS.get(axis) or {}).get("family"),
                "lens": (AXIS_CELLS.get(axis) or {}).get("lens"),
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
            "shared_context_manifest": _review_artifact_path(
                review_dir, "shared-context.manifest.json"
            ),
            "findings": _review_artifact_path(review_dir, "findings.json"),
            "disposition": disposition_path or payload["artifacts"].get("disposition"),
            "verified_disposition": verified_disposition_path
            or payload["artifacts"].get("verified_disposition"),
        }
    )

    if dispatch_result is not None:
        payload["dispatch"] = {
            "requested_axes": requested_axes,
            "requested_axis_count": len(requested_axes),
            "axes": dispatch_axes,
            "elapsed_seconds": dispatch_result.get("elapsed_seconds"),
        }

    if (
        extraction_tasks is not None
        or axis_findings is not None
        or merged_findings is not None
    ):
        usable_axes = [axis for axis, _, _ in (extraction_tasks or [])]
        usable_axis_count = len(usable_axes)
        findings_before_dedup = sum(
            len(findings) for findings in (axis_findings or {}).values()
        )
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
            "coverage_ratio": round(len(axis_findings or {}) / usable_axis_count, 3)
            if usable_axis_count
            else 0.0,
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
    budget: DispatchBudget | None = None,
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
        profile_timeout = profile_def.timeout
        if budget is not None and not budget.can_start(profile_timeout):
            print(
                f"warning: extraction for {axis} skipped — "
                f"{profile_timeout}s needed, {budget.remaining():.0f}s left",
                file=sys.stderr,
            )
            return axis, None
        extraction_path = review_dir / f"{axis}-extraction.json"
        result = _call_llmx(
            provider=profile_def.provider,
            model=profile_def.model,
            context_path=output_path,
            context_manifest_path=None,
            prompt=EXTRACTION_PROMPT,
            output_path=extraction_path,
            schema=FINDING_SCHEMA,
            timeout=profile_timeout,
        )
        if result["exit_code"] != 0:
            print(
                f"warning: extraction for {axis} failed: {result.get('error', 'unknown')}",
                file=sys.stderr,
            )
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
                print(
                    f"warning: extraction for {axis} returned invalid JSON: {e}",
                    file=sys.stderr,
                )
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
        text = (
            f"{f.get('title', '')} {f.get('file', '')} {f.get('description', '')[:200]}"
        )
        words = set(re.findall(r"[a-z_]{4,}", text.lower()))
        # Remove common stop-words that inflate false matches
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
            # Check for overlap with existing findings (keyword Jaccard).
            matched = False
            for existing_fp, existing in seen:
                if (
                    len(fp & existing_fp) > 0
                    and len(fp & existing_fp) / len(fp | existing_fp)
                    > CROSS_MODEL_JACCARD_THRESHOLD
                ):
                    existing.setdefault("also_found_by", []).append(source_label)
                    existing["cross_model"] = True
                    existing["confidence"] = min(
                        1.0, existing.get("confidence", 0.5) + 0.2
                    )
                    matched = True
                    break
            if not matched:
                seen.append((fp, f))
                merged_findings.append(f)

    # Sort: cross-model agreements first, then by severity, then confidence
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    merged_findings.sort(
        key=lambda f: (
            0 if f.get("cross_model") else 1,
            severity_order.get(f.get("severity", "low"), 3),
            -(f.get("confidence", 0)),
        )
    )

    # Renumber
    for i, f in enumerate(merged_findings, 1):
        f["id"] = i

    # Write structured JSON
    structured_path = review_dir / "findings.json"
    structured_path.write_text(
        json.dumps({"findings": merged_findings}, indent=2) + "\n"
    )

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
    sibling_roots: list[Path] | None = None,
) -> str:
    """Verify extracted claims against the actual codebase.

    Checks if cited files and symbols exist. Grades each claim:
    - CONFIRMED: all cited files/symbols found
    - HALLUCINATED: cited file does not exist in project
    - UNVERIFIABLE: no file references to check

    Returns path to verified-disposition.md.
    """
    sibling_roots = sibling_roots or []
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
                f"File: {file_path}:{line_number}"
                if file_path and isinstance(line_number, int) and line_number > 0
                else (f"File: {file_path}" if file_path else ""),
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
            "review",
            "finding",
            "findings",
            "description",
            "category",
            "confidence",
            "source",
            "file",
            "fix",
            "error",
            "warning",
            "coverage",
            "json",
            "path",
            "model",
            "script",
            "line",
            "claim",
            "claims",
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
    # citing data/config files. Order reflects observed frequency: GPT-5.5
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

    # Inflated HALLUCINATED rate (~30-40% in genomics reviews 2026-04-25/26)
    # came from two resolver gaps:
    #   1. rglob() walked .claude/worktrees/ and returned 4× duplicates for
    #      every file → "ambiguous" → discarded.
    #   2. Path-prefixed references like "scripts/controller_reconcile.py"
    #      missed when the actual file is at scripts/orchestrator/
    #      controller_reconcile.py — rglob with path-separator does
    #      suffix-match, not basename-match.
    # Fix: exclude cruft dirs from candidates; fall back to basename-only
    # search when a path-prefixed reference fails.
    _CRUFT_DIRS = (
        ".claude/worktrees",
        ".claude/cache",
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "vendors",
        ".pytest_cache",
        ".ruff_cache",
        ".model-review",
        ".tasks",
        "node_modules",
        "build",
        "dist",
    )

    def _is_cruft(p: Path) -> bool:
        s = p.as_posix()
        return any(
            f"/{d}/" in s or s.endswith(f"/{d}") or s.startswith(f"{d}/")
            for d in _CRUFT_DIRS
        )

    def _filtered_rglob(pattern: str, root: Path | None = None) -> list[Path]:
        return [p for p in (root or project_dir).rglob(pattern) if not _is_cruft(p)]

    _TEXT_VERIFY_SUFFIXES = {
        ".cfg",
        ".clj",
        ".cljc",
        ".css",
        ".edn",
        ".html",
        ".js",
        ".json",
        ".md",
        ".py",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".yaml",
        ".yml",
    }

    def _is_text_verifiable(path: Path) -> bool:
        return path.suffix.lower() in _TEXT_VERIFY_SUFFIXES

    def _resolve_reference(filepath: str) -> tuple[str, Path | None, str]:
        exact_path = project_dir / filepath
        if exact_path.exists():
            return "exact", exact_path, filepath
        candidates = _filtered_rglob(filepath)
        if len(candidates) == 1:
            return "basename", candidates[0], filepath
        if len(candidates) > 1:
            return "ambiguous", None, filepath

        # Path-prefixed reference (e.g. "scripts/foo.py") missed because the
        # file actually lives deeper (e.g. "scripts/orchestrator/foo.py").
        # Fall back to basename-only search.
        if "/" in filepath:
            basename = filepath.rsplit("/", 1)[1]
            base_candidates = _filtered_rglob(basename)
            if len(base_candidates) == 1:
                return "basename_prefix_drop", base_candidates[0], filepath

        # No direct hit — try extension-swap aliases before declaring missing.
        suffix = Path(filepath).suffix
        for alt_ext in _FUZZY_EXT_ALIASES.get(suffix, ()):
            alt_filepath = (
                filepath[: -len(suffix)] + alt_ext if suffix else filepath + alt_ext
            )
            alt_exact = project_dir / alt_filepath
            if alt_exact.exists():
                return "exact_extswap", alt_exact, alt_filepath
            alt_candidates = _filtered_rglob(alt_filepath)
            if len(alt_candidates) == 1:
                return "basename_extswap", alt_candidates[0], alt_filepath

        # Cross-repo: the referenced file may live in a SIBLING repo (e.g. a
        # genomics<->phenome bridge review where half the diff is in phenome).
        # Resolving only against project_dir marks every sibling-repo anchor
        # HALLUCINATED — the dominant false negative on cross-repo packets (a
        # 5-axis bridge review hit 50.8% "hallucinated", burying 2 real bugs).
        # Roots are passed explicitly via --sibling-roots (no auto-scan cost).
        for root in sibling_roots:
            if (root / filepath).exists():
                return "exact_sibling", root / filepath, filepath
        if sibling_roots:
            basename = filepath.rsplit("/", 1)[1] if "/" in filepath else filepath
            sib_hits: list[Path] = []
            for root in sibling_roots:
                sib_hits.extend(_filtered_rglob(basename, root))
            if len(sib_hits) == 1:
                return "basename_sibling", sib_hits[0], filepath

        # Code-SYMBOL reference cited as if it were a file (e.g.
        # "GenomeObserver.observe()", "_VcfRecord", "parse_variant_key()").
        # These are not files, so every branch above misses and the finding gets
        # marked HALLUCINATED — the 3rd anchor-inflation class (after .js/.json
        # ext-swap and cross-repo siblings). A 38%-"hallucinated" genomics close
        # was really ~10%; the rest were real findings citing real symbols.
        # Resolve by grepping source for the definition.
        sym = filepath.strip()
        if sym.endswith("()"):
            sym = sym[:-2]
        if Path(sym).suffix.lower() not in _TEXT_VERIFY_SUFFIXES and re.fullmatch(
            r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", sym
        ):
            leaf = sym.rsplit(".", 1)[-1]
            def_re = re.compile(
                r"^[ \t]*(?:async\s+def|def|class)\s+" + re.escape(leaf) + r"\b", re.M
            )
            sym_hits: list[Path] = []
            for root in (project_dir, *sibling_roots):
                for ext in ("*.py", "*.ts", "*.tsx", "*.js"):
                    for p in root.rglob(ext):
                        if _is_cruft(p):
                            continue
                        try:
                            if def_re.search(
                                p.read_text(encoding="utf-8", errors="ignore")
                            ):
                                sym_hits.append(p)
                        except OSError:
                            continue
                if sym_hits:
                    break
            if sym_hits:
                # Any definition hit means the symbol is real (not a hallucinated
                # file). Multiple hits → pick the first; the goal is "this citation
                # is grounded," not pinpointing one of N overloads.
                return "symbol_def", sym_hits[0], filepath

        return "missing", None, filepath

    claims: list[dict[str, object]] = (
        _parse_structured_claims() or _parse_disposition_claims()
    )

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
            file_refs.append(
                (structured_file, str(structured_line) if structured_line > 0 else "")
            )
        file_refs.extend(
            re.findall(
                r"`?([a-zA-Z_][\w/.-]*\.(?:py|js|ts|md|sh|json|yaml|yml|toml|cfg|sql|html|css|clj|cljc|edn))(?::(\d+))?`?",
                body_text,
            )
        )
        deduped_refs: list[tuple[str, str]] = []
        seen_refs: set[tuple[str, str]] = set()
        for filepath, line_str in file_refs:
            key = (filepath, line_str)
            if key not in seen_refs:
                seen_refs.add(key)
                deduped_refs.append(key)
        file_refs = deduped_refs

        if not file_refs:
            verified.append(
                {
                    **claim,
                    "verdict": verdict,
                    "notes": "no file references or structured file anchors",
                }
            )
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
            elif not _is_text_verifiable(found_path):
                notes.append(
                    f"{display_path} resolved but is binary/non-text; skipped content anchors"
                )
                reference_results.append(("binary", found_path, line_str))
            else:
                reference_results.append((resolution, found_path, line_str))

        if verdict == "HALLUCINATED":
            verified.append({**claim, "verdict": verdict, "notes": "; ".join(notes)})
            continue

        anchor_confirmed = False
        line_corrected = False
        ambiguous_ref = any(
            resolution == "ambiguous" for resolution, _, _ in reference_results
        )
        for resolution, found_path, line_str in reference_results:
            if resolution in {"ambiguous", "binary"}:
                continue
            if resolution == "symbol_def":
                # The reference was a code symbol, not a file:line. We confirmed its
                # definition exists in found_path — that IS the grounding. The model's
                # "line" for a symbol citation is meaningless, so don't line-match.
                anchor_confirmed = True
                continue
            try:
                file_text = found_path.read_text(encoding="utf-8", errors="replace")
                file_lines = file_text.splitlines()
            except OSError:
                try:
                    _disp = str(found_path.relative_to(project_dir))
                except ValueError:
                    _disp = str(found_path)  # sibling-root/absolute path
                notes.append(f"{_disp} unreadable")
                continue

            # found_path may live under a --sibling-root (cross-repo packet), not
            # project_dir — relative_to(project_dir) raises ValueError for it. Guard
            # and fall back to the absolute path (rule #11; the --sibling-roots verify
            # crash, 2026-06-03).
            try:
                relative_display = str(found_path.relative_to(project_dir))
            except ValueError:
                relative_display = str(found_path)
            if line_str:
                line_num = int(line_str)
                if line_num > len(file_lines):
                    line_corrected = True
                    notes.append(
                        f"{relative_display}:{line_num} beyond EOF ({len(file_lines)} lines)"
                    )
                else:
                    start = max(0, line_num - 4)
                    end = min(len(file_lines), line_num + 3)
                    window = "\n".join(file_lines[start:end]).lower()
                    matched = [
                        anchor for anchor in claim_anchors if anchor.lower() in window
                    ]
                    if matched:
                        anchor_confirmed = True
                        notes.append(
                            f"{relative_display}:{line_num} anchors {', '.join(sorted(set(matched)))}"
                        )
                    else:
                        notes.append(f"{relative_display}:{line_num} readable")
            else:
                file_text_lower = file_text.lower()
                matched = [
                    anchor
                    for anchor in claim_anchors
                    if anchor.lower() in file_text_lower
                ]
                if matched:
                    anchor_confirmed = True
                    notes.append(
                        f"{relative_display} anchors {', '.join(sorted(set(matched)))}"
                    )
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
        "hallucination_rate": round(hallucinated / len(verified), 3)
        if verified
        else 0.0,
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
        lines_out.append(
            f"| {v['num']} | {v['verdict']} | {claim_short} | {v.get('notes', '')} |"
        )
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


def run_preflight() -> int:
    """Probe llmx CLI (info + subscription dry-run). Import is optional."""
    import shutil
    import subprocess

    checks: dict = {}
    llmx_bin = shutil.which("llmx")
    checks["llmx_cli"] = {"ok": bool(llmx_bin), "path": llmx_bin}
    if not llmx_bin:
        print(json.dumps(checks, indent=2))
        return 1

    try:
        import llmx  # type: ignore

        checks["llmx_import"] = {
            "ok": True,
            "version": getattr(llmx, "__version__", "?"),
            "python": sys.executable,
            "optional": True,
        }
    except ImportError as exc:
        checks["llmx_import"] = {
            "ok": False,
            "optional": True,
            "error": str(exc),
            "python": sys.executable,
            "note": "CLI probes are authoritative; import only needed for llm_dispatch API path",
        }

    info = subprocess.run(
        [llmx_bin, "info", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    checks["llmx_info"] = {"ok": info.returncode == 0, "exit_code": info.returncode}
    if info.returncode == 0:
        try:
            checks["routing"] = json.loads(info.stdout)
        except json.JSONDecodeError:
            checks["routing_parse"] = {"ok": False}
    else:
        checks["llmx_info_stderr"] = (info.stderr or "")[:500]

    dry = subprocess.run(
        [
            llmx_bin,
            "chat",
            "--dry-run",
            "--subscription",
            "-m",
            "claude-opus-4-8",
            "-e",
            "max",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    checks["dry_run_subscription"] = {
        "ok": dry.returncode == 0,
        "exit_code": dry.returncode,
        "stderr": (dry.stderr or "").strip()[:400],
    }
    if dry.returncode == 0:
        try:
            checks["dry_run_plan"] = json.loads(dry.stdout)
        except json.JSONDecodeError:
            pass

    out = Path(".model-review/preflight-latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))

    oks = [
        v["ok"]
        for k, v in checks.items()
        if isinstance(v, dict) and "ok" in v and k != "llmx_import"
    ]
    return 0 if oks and all(oks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model-review dispatch: context assembly + parallel llmx + output collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Presets: {', '.join(PRESETS.keys())}. Axes: {', '.join(AXES.keys())}.",
    )
    # Context flags are additive (2026-05-07): --context provides a primary pre-assembled
    # narrative; --context-files appends auxiliary file excerpts. Either or both may be
    # used; at least one is required.
    parser.add_argument(
        "--context", type=Path, help="Primary pre-assembled context file (narrative)"
    )
    parser.add_argument(
        "--context-files",
        nargs="+",
        metavar="FILE_SPEC",
        help="Auxiliary file:range specs (e.g., plan.md scripts/ir.py:86-110). Additive with --context.",
    )
    parser.add_argument(
        "--topic",
        default="preflight",
        help="Short topic label (used in output dir name)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Project dir for goals/governance doc discovery (default: cwd)",
    )
    parser.add_argument(
        "--sibling-roots",
        type=Path,
        nargs="*",
        default=[],
        help="Additional repo roots to resolve cross-repo anchors against (e.g. "
        "~/Projects/phenome for a bridge review). Without this, findings that "
        "cite files in a sibling repo are marked HALLUCINATED.",
    )
    parser.add_argument(
        "--axes",
        default=None,
        help="Comma-separated axes or preset (standard, cross2, deep). "
        "Omit to take preset/axes from --dispatch-manifest.",
    )
    parser.add_argument("--allow-non-gpt", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--extract",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable extraction. Enabled by default for user-facing reviews; use --no-extract for debugging-only runs.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After extraction, verify cited files/symbols exist. Implies --extract.",
    )
    parser.add_argument(
        "--cross-talk",
        action="store_true",
        help="Sequential cross-talk: run structure lenses first, inject structural_assumptions "
        "into mechanism passes (cross2/cross4). Default remains parallel.",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        help="JSON file mapping axis names to custom questions (overrides positional question per-axis)",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Probe llmx import/info/subscription dry-run and exit (no review dispatch).",
    )
    parser.add_argument(
        "--scout",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Premise scout (default on). Manifest or --no-scout overrides.",
    )
    parser.add_argument(
        "--context-scope",
        choices=["repo", "packet"],
        default=None,
        help="repo=scout may grep workspace. packet=packet-only review.",
    )
    parser.add_argument(
        "--dispatch-manifest",
        type=Path,
        default=None,
        help="review_gate triage output (dispatch.json) — policy fields when CLI omits them.",
    )
    parser.add_argument(
        "--irreversible",
        action="store_true",
        help="Load-bearing review: block adjudication if executed scout returns conviction=low.",
    )
    parser.add_argument(
        "--force-scout",
        action="store_true",
        help="Proceed to adjudication even when --irreversible and scout conviction=low.",
    )
    parser.add_argument(
        "--fork",
        help="Named design fork for premise scout (default: --topic).",
    )
    parser.add_argument(
        "--budget-seconds",
        type=int,
        default=None,
        metavar="SEC",
        help=(
            "Optional orchestrator wall-clock cap (scout+dispatch+extract). "
            "No limit by default. When set: skip any call whose full profile "
            "timeout cannot fit in remaining time — never truncate timeouts."
        ),
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="Review this for logical gaps, missed edge cases, and principles alignment.",
        help="Review question for all models",
    )

    args = parser.parse_args()

    if args.preflight:
        return run_preflight()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    # At least one of --context / --context-files must be provided (mutex relaxed 2026-05-07)
    if not args.context and not args.context_files:
        print(
            "error: at least one of --context or --context-files is required",
            file=sys.stderr,
        )
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    if args.dispatch_manifest:
        if not args.dispatch_manifest.is_file():
            print(
                f"error: dispatch manifest {args.dispatch_manifest} not found",
                file=sys.stderr,
            )
            return 1
        manifest = apply_dispatch_manifest(args, args.dispatch_manifest)
        schema_err = validate_dispatch_schema(manifest)
        if schema_err:
            print(f"error: {schema_err}", file=sys.stderr)
            return 1
        if manifest.get("schema_version") is None:
            print(
                "warning: dispatch manifest missing schema_version (pre-v1); "
                "re-run review_gate triage",
                file=sys.stderr,
            )
        print(f"note: dispatch policy from {args.dispatch_manifest}", file=sys.stderr)
        blockers = dispatch_manifest_blockers(manifest)
        if blockers:
            for blocker in blockers:
                print(f"error: {blocker}", file=sys.stderr)
            return 1

    if args.scout is None:
        args.scout = True
    if args.context_scope is None:
        args.context_scope = "repo"
    if args.axes is None:
        args.axes = "standard"

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

    # Create output directory (scout writes here before context assembly)
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    budget = DispatchBudget.from_seconds(args.budget_seconds)
    if budget.active:
        print(
            f"note: dispatch budget {args.budget_seconds}s — "
            "axes skip if profile timeout cannot fit",
            file=sys.stderr,
        )

    premise_scout_path: Path | None = None
    scout_result: PremiseScoutResult | None = None
    primary_context = args.context
    run_scout = should_run_premise_scout(
        scout=bool(args.scout),
        context_scope=args.context_scope,
        has_context=bool(primary_context),
    )
    if args.scout and args.context_scope == "packet":
        print(
            "note: --context-scope packet — repo premise scout disabled (packet-only)",
            file=sys.stderr,
        )
    elif args.scout and not primary_context and args.context_files:
        print(
            "warning: --scout needs --context (narrative packet); skipping premise scout",
            file=sys.stderr,
        )
    elif run_scout and primary_context:
        scout_result = run_premise_scout(
            review_dir=review_dir,
            project_dir=project_dir,
            context_path=primary_context,
            topic=args.topic,
            question=args.question,
            fork=args.fork,
            budget=budget,
        )
        if scout_result.markdown_path:
            premise_scout_path = scout_result.markdown_path
            print(
                f"Premise scout complete → {premise_scout_path} "
                f"(conviction={scout_result.conviction})",
                file=sys.stderr,
            )
        elif scout_result.skip_reason:
            print(
                f"warning: premise scout skipped ({scout_result.skip_reason}); "
                f"see {scout_result.json_path}",
                file=sys.stderr,
            )

    gate_exit = check_scout_conviction_gate(
        scout_result,
        irreversible=bool(args.irreversible),
        force=bool(args.force_scout),
    )
    if gate_exit is not None:
        return gate_exit

    print(
        f"Dispatching {len(axis_names)} queries: {', '.join(axis_names)}",
        file=sys.stderr,
    )

    # Assemble context
    ctx_files = build_context(
        review_dir,
        project_dir,
        args.context,
        axis_names,
        context_file_specs=args.context_files,
        premise_scout_path=premise_scout_path,
    )

    governance_path = find_governance(project_dir)

    # Load per-axis question overrides
    question_overrides = None
    if args.questions:
        if not args.questions.exists():
            print(f"error: questions file {args.questions} not found", file=sys.stderr)
            return 1
        try:
            question_overrides = json.loads(args.questions.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"error: invalid questions file {args.questions}: {exc}",
                file=sys.stderr,
            )
            return 1

    # Dispatch and wait (parallel default; --cross-talk for structure→mechanism injection)
    dispatch_fn = dispatch_cross_talk if args.cross_talk else dispatch
    if args.cross_talk:
        structure_axes, mechanism_axes, _ = split_axes_by_lens(axis_names)
        if not structure_axes or not mechanism_axes:
            print(
                "warning: --cross-talk needs both structure and mechanism lenses; "
                "falling back to parallel dispatch",
                file=sys.stderr,
            )
            dispatch_fn = dispatch
    result = dispatch_fn(
        review_dir,
        ctx_files,
        axis_names,
        args.question,
        bool(governance_path),
        question_overrides,
        budget=budget,
    )
    if budget.active:
        rem = budget.remaining()
        result["budget_seconds"] = args.budget_seconds
        result["budget_remaining_seconds"] = round(rem, 1) if rem is not None else 0.0
    effective_policy = build_effective_policy(args)
    if args.dispatch_manifest:
        effective_policy["dispatch_manifest"] = str(args.dispatch_manifest)
    receipt_path = write_execution_receipt(
        review_dir,
        axis_names=axis_names,
        dispatch_result=result,
        effective_policy=effective_policy,
    )
    result["execution_receipt"] = str(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if receipt["overall"] != "complete":
        print(
            f"error: dispatch incomplete (overall={receipt['overall']}); "
            f"see {receipt_path}",
            file=sys.stderr,
        )
    if scout_result and scout_result.json_path:
        result["premise_scout"] = str(scout_result.json_path)
        if scout_result.markdown_path:
            result["premise_scout_md"] = str(scout_result.markdown_path)
    failures = collect_dispatch_failures(result, ctx_files)
    if failures or receipt["overall"] != "complete":
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
        disposition_path = extract_claims(review_dir, result, budget=budget)
        coverage_path = review_dir / "coverage.json"
        if coverage_path.exists():
            result["coverage"] = str(coverage_path)
            print(f"Coverage written to {coverage_path}", file=sys.stderr)
        if disposition_path:
            result["disposition"] = disposition_path
            print(f"Disposition written to {disposition_path}", file=sys.stderr)

            # Optional verification phase
            if args.verify:
                verified_path = verify_claims(
                    review_dir,
                    disposition_path,
                    project_dir,
                    sibling_roots=args.sibling_roots,
                )
                result["verified_disposition"] = verified_path
                print(
                    f"Verified disposition written to {verified_path}", file=sys.stderr
                )

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
