# Model Review Context Packet

- Project: `/Users/alien/Projects/genomics`
- Axes: `arch,formal`

## Preamble

## PROJECT CONSTITUTION (verbatim — review against these, not your priors)

# Constitution

**Human-protected.** Agent may propose changes but must not modify without explicit approval.

Canonical home: `CLAUDE.md` under `## Constitution`.

This rule file is the compact auto-loaded extract. Keep it operational. Do not
duplicate project strategy, domain trivia, or rule content that belongs in
specialized files.

## Generative Principle

> Maximize trustworthy semantic genomic output while increasing the system's
> rate of error correction about runtime, contracts, and scientific claims.

## Principles

1. **Semantic output, not downstream medical inference.** This repo owns
   canonical semantic genomic outputs, not downstream medical advice or
   consumer-facing narrative synthesis.
2. **One path owns meaning.** `CaseBundle` and explicit consumer contracts own
   semantics. Stage artifacts and ad hoc loaders are compute/debug paths, not
   alternate product truths.
3. **Operator surfaces are in scope.** Scheduling, status, failure triage,
   artifact inspection, contract inspection, rerun diffs, and cost visibility
   are legitimate repo work. They must not silently become consumer contracts.
4. **Fail loud on drift.** Hidden fallbacks, stale schemas, ambiguous state,
   and duplicate truths are correctness failures.
5. **Architectural enforcement beats reminders.** If the same failure recurs
   twice and enforcement is feasible, prefer a hook, test, assertion, or typed
   boundary.
6. **Action default for implementation.** Coding/debugging should proceed
   without asking unless the change is irreversible, external-facing, or risks
   a real contract break. Architecture/research starts with a short plan.
7. **Do not stop at partial correctness while work is still tractable.** Use
   checkpoints; do not confuse pause points with completion.
8. **High-signal expansion is allowed; speculative churn is not.** New
   analyses are justified by real gaps or material improvements, not novelty.
9. **Delete superseded paths after migration.** Compatibility seams need a
   named live dependency and a removal condition.
10. **Review where silent semantic failure is likely.** Prefer hooks/tests for
    most changes. Use cross-model review for interpretation-semantics changes,
    policy/threshold changes, and major boundary migrations.

## Autonomy Boundaries

### Hard limits

- Do not publish, share, or expose genomic data externally.
- Do not delete raw CRAM/VCF/FASTQ source data.
- Do not build consumer-facing medical/advice/reporting surfaces here without
  explicit approval.
- Do not add silent semantic fallbacks or preserve conflicting centers of truth
  once a migration target is known.
- Do not modify files outside this repo without explicit instruction.

### Autonomous

- Implement, debug, validate, and refactor pipeline, contract, and
  operator-surface code.
- Run stages, reruns, downloads, and validation gates.
- Add hooks, tests, assertions, and typed boundaries after repeated failures.
- Integrate high-signal papers, tools, databases, and analyses in the active
  assay lane.
- Write path-dependent decisions and audit artifacts once the code/evidence
  basis is real.

## Self-Improvement Governance

- The agent may change pipeline code, contract code, operator surfaces, hooks,
  tests, and most project-local operational tooling.
- Human approval is required for changes to this constitution, `docs/GOALS.md`,
  `CLAUDE.md`, external data exposure, and knowingly breaking an externally
  used contract without a migration plan.
- Keep constitutional material short. Domain-specific evidence rules, Modal
  gotchas, and assay-specific invariants belong in dedicated rule files.
- New enforcement should point to a concrete failure mode, repeated correction,
  or measurable wasted work pattern.

## Session Architecture

- Coding and debugging default to end-to-end completion when feasible.
- Architecture or research starts with a short plan, then execution.
- Use the existing 4-hour / 100-tool-call checkpoint rule for long debugging
  sessions.
- Prefer fresh-session handoffs for long architecture/research streams; keep
  persistence for coding/debugging when active state still matters.
- Same-model peer review is weak evidence. When review matters, prefer
  heterogeneous models or architectural validation of outputs.

## Pre-Registered Tests

- `0` new consumer-facing raw-artifact readers without explicit waiver.
- Repeated corrections about early stopping, hidden state, or duplicate work
  trend down over time.
- Duplicate/orphan Modal incidents decrease after control-plane and
  operator-surface work.
- Operator surfaces cover scheduling, stage state, failure triage, artifact
  inspection, and rerun diffs without routine log spelunking.
- Recurring failure classes graduate into hooks/tests/assertions rather than
  remaining chat-only reminders.

## PROJECT GOALS

# Genomics Interpretation Engine — Goals

> Owner: human. Agents may propose changes but must not modify without explicit approval.

## Mission

Turn sequencing inputs into trusted, evidence-graded genomic interpretation artifacts. This repo is an **interpretation engine** in the narrow sense: it takes sequencing inputs in and emits semantic structured outputs out. Business logic, consumer-facing medical/reporting surfaces, product UX, and delivery happen elsewhere.

**The cardinal rule: don't emit wrong claims that downstream systems could mistake for advice.** A retracted or overstated finding costs more trust than a missed finding. When insight and certainty conflict, surface the uncertainty explicitly through evidence tiers, not hide it or flatten everything to one confidence level.

This also means the engine should not merely emit findings; it should preserve the **scientific claim graph** behind them. Executable claims that affect output, policy, or interpretation should resolve to stable provenance and epistemic context: what external source they rest on, what internal derivation transformed that source, what agent work product contributed, and what later verification actually checked. Comments may assist humans, but comments are not the source of truth.

## Domain

- WGS (currently 30x Nebula, GRCh38; blood WGS and long-read lanes expected soon).
- Input handling should accommodate pointed-at sample sources, not just one fixed local CRAM workflow. Today that mostly means CRAM; soon it may also mean FASTQ or assay-specific ingest paths.
- Multi-sample by design. Each CRAM runs independently through the same pipeline with sample-isolated paths. No N=1 assumptions in shared code.
- Genomics owns canonical semantic outputs end-to-end. Phenotype context, behavioral overlays, and consumer-facing product surfaces are downstream consumers, not co-owners of the reasoning.

## Strategy

### 1. Reproducible analysis backend
Modal serverless compute turns raw sequencing data into validated intermediate artifacts reproducibly. Modal is the execution layer, not the architectural center.

### 2. Canonical interpreted outputs
One canonical output layer that all downstream consumers share. Stage directories are backend compute artifacts. The contract surface is semantic structured output with evidence labels, not raw stage files.

### 3. Finished semantic output, not downstream medical inference
This repo emits findings that already contain evidence grading, provenance, confidence context, and tiering. It should be strong enough that downstream consumers do not need to reconstruct the scientific meaning from raw stage artifacts. But it stops short of downstream medical synthesis, end-user narrative, or advice.

Finished interpretation also requires **governed scientific claims**. The long-term contract is not just "a field has an evidence grade"; it is "each product-significant claim is stably addressable, source-backed, derivation-aware, and explicit about whether it is supported evidence, research-only synthesis, or unverified agent work."

### 4. Agent-native development
Agents write and maintain all code. Enterprise-grade patterns (typed contracts, deep validation, architectural lint, hook enforcement) are the norm, not aspirational — agent dev cost is negligible compared to the error surface they prevent. Simplicity is preferred when it achieves the same correctness, but complexity is not avoided on cost grounds.

### 5. Unattended execution gates rollout
The repo already has broad analytical coverage across variant calling, annotation, PRS, pharmacogenomics, structural analysis, noncoding interpretation, and integrative analyses. The gating problem is no longer "invent more activity"; it is "run a pointed-at sample end to end without hand holding, silent success, or boundary ambiguity."

Multi-sample rollout matters only after unattended clean runs are normal. New analyses still enter when:
- A new assay type arrives (long-read, methylation)
- A database, paper, or tool materially improves an existing interpretation
- A genuinely valuable new raw output or analysis closes a real gap in the active assay lane

### 6. Operator-first development surfaces
Internal operator and developer surfaces are in scope. The repo should make scheduling, status, failure triage, artifact inspection, contract inspection, rerun diffing, and cost visibility easier over time. Humans maintaining the engine should not have to reconstruct state by spelunking raw files and Modal logs.

### 7. Automated freshness
Staying current is event-driven and automated, not manual or cadenced. ClinVar reclassifications, CPIC guideline updates, new tool versions, and relevant papers should propagate through the pipeline via monitoring and selective rerun — not bulk refresh cycles or human-initiated sweeps.

### 8. Source-governed reasoning
Scientific authority should live in typed registries and verifiable tooling, not in ad hoc prose. The engine should distinguish:
- external sources (papers, databases, guidelines)
- internal derivations (benchmarks, calibrations, symbolic/math work)
- agent work products (LLM syntheses, extraction runs, reviews)
- verification events (full-text review, citation-context check, benchmark reproduction, API validation)

The intent is not to make every comment citation-complete. The intent is to make every executable scientific claim machine-auditable and every user-visible interpretation honest about what kind of support it has.

## Architecture Boundary

```text
genomics/                        ← THIS REPO
  sequencing input → compute → semantic interpretation → structured output
  Evidence grading, provenance, confidence, tiering
  Operator/developer surfaces for scheduling, status, debugging, auditing
  167 stages on Modal serverless

downstream consumers (other repos):
  selve/       — personal context, phenotype overlay, behavioral data
  future UI    — web product surface
  future API   — programmatic access
  business     — pricing, delivery, customer management
```

- **Genomics owns**: compute backend, interpretation logic, evidence labeling, finding tiering, canonical structured output, and internal operator/developer surfaces needed to run and maintain the engine.
- **Genomics does NOT own**: consumer-facing product UX, medical report design, downstream narrative synthesis, consumer onboarding, business logic, pricing, delivery channels.
- **Consumer contracts**: downstream projects consume genomics output as a stable API-like contract. Changes to output schema are versioned and announced.

## Success Metrics

| Metric | Measures | Why it matters |
|--------|----------|----------------|
| Trustworthiness | Retraction rate, false-claim rate | Wrong output is worse than missing output |
| Pipeline reliability | Stage pass rate, reproducibility, no silent success, no ambiguous run state | The engine must run unattended before it can scale |
| Contract stability | Breaking changes to output schema per quarter | Downstream consumers need reliability |
| Operator visibility | Coverage of status, artifact, failure, scheduling, and diff surfaces | Humans should supervise the engine, not reconstruct it from raw files |
| Curation accuracy | Auto-classify precision, PGx correctness, evidence-grade accuracy | The interpretation must still be right |
| Claim governance | Fraction of product-significant claims with stable provenance, epistemic tags, and verification state | Scientific correctness should be auditable, not implicit |
| Output completeness | Useful raw-output and analysis coverage for the active assay lane | High-signal new analyses are still valuable when they close real gaps |
| Freshness | Time from upstream change to reflected output | The engine must stay current |

Priority order when metrics conflict:
1. Trustworthiness
2. Pipeline reliability
3. Contract stability
4. Operator visibility
5. Curation accuracy
6. Claim governance
7. Output completeness
8. Freshness

## Time Horizon

The engine has broad analytical coverage, but rollout is still gated by operational reliability. Remaining work:

- **Near term:** Make the active short-read lane run cleanly for a pointed-at sample without hand holding, silent success, or repeated debugging.
- **Near term:** Finish the current boundary cleanup so `CaseBundle` is the semantic output, consumer contracts are explicit, and product-boundary loaders fail clearly.
- **Near term:** Improve operator/developer surfaces so scheduling, stage state, artifacts, failures, reruns, and diffs are easier to inspect.
- **Ongoing:** Continue high-signal integrations when a paper, tool, or analysis materially improves the active assay lane.
- **Ongoing:** Continue source-governed reasoning and scientific-graph work here as enabling infrastructure; if it generalizes cleanly, extract it to a separate repo later.
- **Ongoing:** Automated freshness — research cron jobs, database monitors, selective reruns when upstream changes.
- **When unattended short-read runs are normal:** Run additional friend/family samples through the same pipeline with sample isolation and minimal operator intervention.
- **When new assays arrive:** Long-read lane (PacBio), blood WGS, potentially methylation. These are expected soon, but they should not displace the short-read reliability gate.

## Resource Constraints

| Resource | Status | Implication |
|----------|--------|-------------|
| Human attention | Scarce | Engine should run autonomously. Human reviews findings, not pipeline mechanics |
| Agent coding capacity | Abundant | Dev cost is ~1/100th of pre-AI. Don't avoid complexity on cost grounds |
| Trust | Extremely scarce | Protect with evidence labels, provenance, calibration, and retractions |
| Modal compute | Available but not free | Spend on correctness, but duplicate/orphan/wasteful runs are still a bug |
| Storage / databases | Available | Keep reference data rich and current |

## Finding Tiers

| Tier | Examples | Evidence floor |
|------|----------|----------------|
| **Clinical** | Pathogenic variants, PGx, carrier status, ACMG-SF | C3+ (ClinVar expert-reviewed or better) |
| **High-confidence personal** | PRS near thresholds, ancestry, strong functional evidence | B2+ (functional assay or cohort study) |
| **Exploratory** | Weak literature signals, in silico predictions, network analysis, entertainment genetics | E5+ (any evidence, clearly labeled) |

All tiers are retained. Exploratory stages run and emit output — they are evidence-graded, not suppressed. The tier label IS the quality control. ~12 stages have formal decision value; ~15 have conditional value; ~140 are exploration-grade curiosity. All are legitimate outputs when labeled honestly.

## Secondary Artifacts

- **Agent methodology:** The process of building a 167-stage interpretation engine with AI agents — constitutions, adversarial reviews, concept discovery, epistemic auditing — is a first-class secondary artifact. It transfers to any domain where agents build complex systems.
- **Reusable infrastructure:** Calibration harnesses, typed evidence contracts, provenance workflows, agent hooks, and curation tooling are reusable across projects and potential future products.

## Deferred Scope (not this repo)

- Consumer-facing product surfaces (web UI, mobile, API gateway)
- Business logic (pricing, tiers, customer management)
- Medical report design, narrative generation, and downstream advice
- EHR integration, regulatory certification
- Real-time streaming analysis
- Multi-sample joint calling (independent runs are sufficient)
- Consumer-facing dashboard expansion

## Exit / Pivot Conditions

- If a commercial clinical lab produces better interpretation at reasonable cost, this engine becomes a validation/comparison tool rather than a primary interpreter.
- If expansion compromises trust, narrow scope before scaling.
- If a new architecture clearly reduces the semantic error surface, migrate rather than preserve inertia.
- If the scientific-graph / reasoning substrate generalizes beyond genomics, extract it to its own repo and let genomics consume it rather than forcing this repo to become the general reasoning home.
- If the methodology artifact (agent-built science) proves more valuable than the genomics output, the project's identity may shift accordingly.

---
*Created: 2026-02-28. Revised: 2026-03-31 — shifted to interpretation platform framing. Revised: 2026-04-05 — narrowed to interpretation engine (CRAM→output); business/product/consumer surfaces out of scope; engine declared nearly complete; exploration stages retained with evidence grading; agent-native development posture; automated freshness replaces manual expansion. Revised: 2026-04-09 — interpretation narrowed to semantic output rather than downstream medical inference; internal operator/developer surfaces brought explicitly in scope; unattended short-read runs set as rollout gate; high-signal new analyses remain in scope; reasoning substrate kept as enabling infrastructure with possible later extraction.*

## DEVELOPMENT CONTEXT

# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler or hacky approaches because they are faster to implement
- Cost-benefit analysis should filter on maintenance burden, supervision cost, complexity budget, and blast radius — not creation effort
- Implementation effort is not a meaningful cost dimension here; only ongoing drag matters

## Provided Context

### /Users/alien/Projects/genomics/.model-review/2026-04-10-genomics-status-close-context.md

```text
# Close Review Packet
## Scope
- Target users: personal operator
- Scale: one active sample, designed for many stages
- Rate of change: frequent operator/debug churn
## Context
Review the repo-local status reconciliation migration for correctness, mismatch semantics, and missing validation.

## File: .agents/skills/genomics-status/SKILL.md
```
---
name: genomics-status
description: Quick pipeline status check. Run this when the user asks about pipeline status, what's done, what's running, or what's next.
user-invocable: true
---

# Genomics Status Reconciliation

Use this skill to answer `what is happening right now` for this repo.
Do not collapse the pipeline to `done / running / failed / pending`.

Shared contract:
`/Users/alien/Projects/skills/modal/references/status-reconciliation.md`

## Truth Surfaces In This Repo

- `live runtime signal` -> `genomics_status.py` active runtime, progress files, current log snapshots
- `orchestrator truth` -> control-plane rows from `genomics_status.py` / `just pipeline-status`
- `worker outcome` -> immutable stage receipts under `data/results/<stage>/attempts/*/receipt.json`
- `local usability` -> downloaded local bridge under `data/wgs/analysis/...`
- `spend attribution` -> `just modal-cost`

## Default Workflow

1. Run:

```bash
uv run python3 scripts/genomics_status.py
```

2. Read the reconciliation section first. For each stage mentioned, report:
`question -> primary source -> supporting sources -> mismatch class -> next action`

3. If the answer is still unclear, drill down by surface instead of rerunning the same command blindly:

```bash
uv run python3 scripts/genomics_status.py --volume
uv run python3 scripts/genomics_status.py --run-id <run_id>
uv run python3 scripts/genomics_status.py --apps
just pipeline-status
just modal-cost
```

## What To Look For

- `running_signal`: runtime signal agrees that work is active now
- `stale_receipt`: latest receipt still says running, but fresh runtime evidence is gone
- `incomplete_attempt`: control plane expects active work, but there is no matching runtime signal
- `bridge_failed`: worker completed, but local bridge is missing or unusable
- `local_stale`: local results exist, but a newer run is active or the latest attempt failed
- `failed_receipt`: latest worker receipt is terminal failure

## Repo-Specific Rules

- Trust the control plane for `what should be running`.
- Trust the worker receipt for `what the worker said happened`.
- Trust local files only for `can I use this result locally`.
- Treat `_STATUS.json` / receipt state as insufficient proof of live liveness by itself.
- Treat spend as a separate report; use `just modal-cost` instead of inferring cost from status.

```

## File: scripts/genomics_status.py
```
#!/usr/bin/env python3
"""
Comprehensive pipeline status dashboard for personal WGS analysis.

Derives all display entries from the STAGES registry in pipeline_stages.py,
with explicit EXTRA_CHECKS for non-stage display items.

Uses a single lightweight Modal function to probe the entire volume at once,
instead of N separate `modal volume ls` CLI calls.

Usage:
  uv run python scripts/genomics_status.py          # full dashboard
  uv run python scripts/genomics_status.py --volume  # Modal volume only
  uv run python scripts/genomics_status.py --local   # local files only
  uv run python scripts/genomics_status.py --apps    # running Modal apps
  uv run python scripts/genomics_status.py --estimate # runtime estimates
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import modal
from base_images import inject_standard_local_files
from modal_utils import DATA_DIR, SAMPLE_ID, VOLUME
from orchestrator.controller import ControllerService, load_store_from_env
from pipeline_stages import STAGES, topological_sort
from progress_contract import coerce_snapshot, summarize_progress
from variant_evidence_core import fmt_size
from wgs_config import Paths, canonical_status_root

VOLUME_NAME = VOLUME
_LOCAL_PATHS = Paths()
LOCAL_RAW = _LOCAL_PATHS.input_dir
LOCAL_ANALYSIS = _LOCAL_PATHS.analysis_root
app = modal.App("genomics-status")
vol = modal.Volume.from_name(VOLUME_NAME)
image = inject_standard_local_files(
    modal.Image.debian_slim(python_version="3.12").pip_install("pydantic", "beartype"),
    include_pipeline_core=True,
    include_evidence_core=True,
    extra_local_files=[("scripts/pipeline_stages.py", "/root/pipeline_stages.py")],
)


# ── Display name mapping ───────────────────────────────────────────────────
# Maps stage names → human-readable names for the dashboard.
# Stages not listed here use name.replace("_", " ").title().

_STAGE_DISPLAY_NAMES: dict[str, str] = {
    "pharmcat": "PharmCAT",
    "pgx_regenotype_missing": "PGx regenotype",
    "pharmcat_core_outside": "PharmCAT (outside calls)",
    "vep": "VEP annotation",
    "slivar": "Slivar filtering",
    "cpsr": "CPSR",
    "mito_mutect2": "Mito calling",
    "expansion_hunter": "ExpansionHunter",
    "delly": "DELLY (SVs)",
    "manta": "Manta SV",
    "annotsv": "AnnotSV",
    "annotsv_manta": "AnnotSV (Manta)",
    "sv_merged": "Manta merged",
    "glimpse2": "GLIMPSE2 imputation",
    "ancestry": "Ancestry PCA",
    "ancestry_admixture": "Ancestry admixture",
    "ancestry_eur_fine": "Ancestry EUR fine",
    "local_ancestry": "Local ancestry",
    "ancient_dna_pca": "Ancient DNA PCA",
    "roh_gnomad": "ROH (gnomAD)",
    "prs": "PRS (6 traits)",
    "prs_percentile": "PRS percentile",
    "prs_expanded": "PRS expanded",
    "gwas_catalog": "GWAS Catalog",
    "rare_variant_triage": "Rare-variant triage",
    "exomiser": "Exomiser",
    "chip_screening": "CHIP screening",
    "carrier_screening": "Carrier screening",
    "metagenomics": "Kraken2",
    "hla_optitype": "HLA Class I",
    "hla_class2": "HLA Class II",
    "encode_ccre": "ENCODE cCRE",
    "abc_enhancer": "ABC enhancer",
    "spliceai": "CI-SpliceAI",
    "noncoding_triage": "Non-coding triage",
    "haplogroups": "Haplogroups",
    "mtcn": "Mito CN",
    "nutrigenomics": "Nutrigenomics",
    "deepvariant": "DeepVariant",
    "aldy": "Aldy (CYP2D6)",
    "biomedical_enrichment": "Biomedical enrichment",
    "whatshap": "WhatsHap phasing",
    "shapeit5_scaffold": "SHAPEIT5 scaffold",
    "jarvis_macie": "JARVIS/MACIE",
    "rasp_ddg": "RaSP ddG",
    "premode": "PreMode GoF/LoF",
    "sei": "Sei regulatory",
    "sven_sv": "SVEN SV",
    "rexpert": "RExPRT STR",
}

_GROUP_DISPLAY_NAMES: dict[str, str] = {
    "dl_variant_scores": "DL variant scores",
}


def _format_progress_suffix(progress_payload: dict[str, Any] | None) -> str:
    def _legacy_summary(payload: dict[str, Any] | None) -> str:
        if not payload:
            return ""
        percent = payload.get("compressed_progress_pct") or payload.get("percent")
        current = payload.get("compressed_bytes_read") or payload.get("current")
        total = payload.get("compressed_bytes_total") or payload.get("total")
        step = payload.get("active_block") or payload.get("step") or ""
        message = payload.get("message") or payload.get("status") or ""
        parts: list[str] = []
        if percent not in (None, ""):
            try:
                parts.append(f"{float(percent):.1f}%")
            except (TypeError, ValueError):
                parts.append(str(percent))
        if current not in (None, "") and total not in (None, "", 0):
            try:
                parts.append(f"{fmt_size(int(current))}/{fmt_size(int(total))}")
            except (TypeError, ValueError):
                parts.append(f"{current}/{total}")
        elif current not in (None, ""):
            parts.append(str(current))
        if step:
            parts.append(str(step).strip())
        if message:
            parts.append(str(message))
        return " ".join(parts).strip()

    snapshot = coerce_snapshot(progress_payload)
    if snapshot is None:
        return _legacy_summary(progress_payload)
    summary = summarize_progress(snapshot)
    if not summary:
        summary = _legacy_summary(progress_payload)
    if snapshot.is_stale():
        summary = f"{summary} stale" if summary else "stale"
    return summary


def _parse_timestamp(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_duration_compact(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    total_seconds = max(0, int(round(float(seconds))))
    if total_seconds < 60:
        return f"{total_seconds}s"
    if total_seconds < 3600:
        minutes, remainder = divmod(total_seconds, 60)
        return f"{minutes}m" if remainder == 0 else f"{minutes}m{remainder:02d}s"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes:02d}m"


def _elapsed_seconds_from_progress(
    progress_payload: dict[str, Any] | None,
    *,
    fallback_elapsed_s: float | int | None = None,
) -> float | None:
    candidates: list[object] = []
    if isinstance(progress_payload, dict):
        details = progress_payload.get("details")
        if isinstance(details, dict):
            candidates.append(details.get("elapsed_s"))
        candidates.append(progress_payload.get("elapsed_s"))
    candidates.append(fallback_elapsed_s)
    for value in candidates:
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _runtime_budget_suffix(
    stage_name: str,
    *,
    progress_payload: dict[str, Any] | None = None,
    updated_at: str = "",
    fallback_elapsed_s: float | int | None = None,
    planned_duration_estimate_min: int | None = None,
    now: datetime | None = None,
) -> str:
    stage_spec = STAGES.get(stage_name)
    elapsed_s = _elapsed_seconds_from_progress(progress_payload, fallback_elapsed_s=fallback_elapsed_s)
    estimate_min = planned_duration_estimate_min
    if estimate_min in (None, 0) and stage_spec is not None and stage_spec.duration_estimate_min > 0:
        estimate_min = stage_spec.duration_estimate_min
    timeout_s = stage_spec.timeout if stage_spec is not None and stage_spec.timeout > 0 else None

    observed_at = _parse_timestamp(updated_at)
    age_s: float | None = None
    if observed_at is not None:
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        age_s = max(0.0, (current_time.astimezone(UTC) - observed_at).total_seconds())

    max_silence_s: int | None = None
    if isinstance(progress_payload, dict):
        raw_silence = progress_payload.get("max_silence_s")
        if raw_silence in (None, ""):
            details = progress_payload.get("details")
            if isinstance(details, dict):
                raw_silence = details.get("max_silence_s")
        if raw_silence not in (None, ""):
            try:
                max_silence_s = int(raw_silence)
            except (TypeError, ValueError):
                max_silence_s = None

    parts: list[str] = []
    if elapsed_s is not None:
        parts.append(f"elapsed {_format_duration_compact(elapsed_s)}")
    if estimate_min not in (None, 0):
        parts.append(f"est {_format_duration_compact(int(estimate_min) * 60)}")
    if timeout_s is not None:
        if elapsed_s is not None and elapsed_s < timeout_s:
            parts.append(f"timeout in {_format_duration_compact(timeout_s - elapsed_s)}")
        else:
            parts.append(f"timeout {_format_duration_compact(timeout_s)}")
    if age_s is not None:
        parts.append(f"age {_format_duration_compact(age_s)}")

    status_notes: list[str] = []
    if estimate_min not in (None, 0) and elapsed_s is not None:
        estimate_s = int(estimate_min) * 60
        if elapsed_s >= estimate_s * 1.25:
            status_notes.append("over est")
        elif elapsed_s >= estimate_s * 0.9:
            status_notes.append("near est")
    if max_silence_s and age_s is not None and age_s > max_silence_s:
        status_notes.append(f"stale>{_format_duration_compact(max_silence_s)}")
    if status_notes:
        parts.append(", ".join(status_notes))
    return " | ".join(parts)


def _worker_updated_at(
    receipt_payload: Any,
    progress_payload: Any,
) -> str:
    if isinstance(progress_payload, dict):
        progress_updated_at = str(progress_payload.get("updated_at", "") or "").strip()
        if progress_updated_at:
            return progress_updated_at
        details = progress_payload.get("details")
        if isinstance(details, dict):
            detail_updated_at = str(details.get("updated_at", "") or "").strip()
            if detail_updated_at:
                return detail_updated_at
    if hasattr(receipt_payload, "timestamp"):
        return str(getattr(receipt_payload, "timestamp", "") or "")
    if isinstance(receipt_payload, dict):
        return str(receipt_payload.get("timestamp", "") or "")
    return ""


# ── Non-stage display entries ─────────────────────────────────────────────
# These appear in the dashboard but aren't registered as pipeline stages.

EXTRA_CHECKS: list[dict[str, Any]] = [
    {
        "name": "CH germline risk",
        "path": "results/chip",
        "key_suffixes": ["ch_germline_risk.tsv"],
    },
    {
        "name": "QC spot-check",
        "path": "results/qc_spotcheck",
        "key_suffixes": ["qc_spotcheck_report.json"],
        "summary_file": "qc_spotcheck_report.json",
    },
    {
        "name": "ACMG classification",
        "path": "results/acmg",
        "key_suffixes": ["acmg_classifications.tsv", "acmg_summary.json"],
        "summary_file": "acmg_summary.json",
    },
]

# Extra local-only result dirs not represented by Modal stages.
EXTRA_LOCAL_DIRS: list[tuple[str, Path]] = [
    ("Trait variants", LOCAL_ANALYSIS / "trait_variants"),
    ("SNPedia scan", LOCAL_ANALYSIS / "snpedia"),
]


# ── Derive volume checks from STAGES ──────────────────────────────────────


def _output_suffix(output: str) -> str:
    """Extract file suffix from output path (keeps leading dot after {SAMPLE})."""
    filename = output.rsplit("/", 1)[-1]
    return filename.replace("{SAMPLE}", "")


def _output_dir(output: str) -> str:
    """Extract the directory from an output path."""
    return output.rsplit("/", 1)[0] if "/" in output else output


def _local_subdir(output: str) -> str:
    """Map a stage output path to its local analysis subdirectory."""
    return _output_dir(output).removeprefix("results/").removeprefix("analysis/")


def _build_volume_checks() -> list[dict[str, Any]]:
    """Derive volume check list from STAGES registry + EXTRA_CHECKS."""
    checks: list[dict[str, Any]] = [
        {
            "name": "Input (CRAM+VCF)",
            "path": "input",
            "key_suffixes": [".cram", ".cram.crai", ".vcf.gz", ".vcf.gz.tbi"],
        },
        {"name": "Reference genome", "path": "reference", "key_suffixes": [".fa", ".fa.fai"]},
    ]

    seen_groups: set[str] = set()
    for name in topological_sort(STAGES):
        stage = STAGES[name]

        if stage.display_group:
            if stage.display_group in seen_groups:
                continue
            seen_groups.add(stage.display_group)
            group_stages = [s for s in STAGES.values() if s.display_group == stage.display_group]
            all_outputs = []
            for gs in group_stages:
                all_outputs.extend(gs.outputs)
            suffixes = [_output_suffix(o) for o in all_outputs]
            dirs = list(dict.fromkeys(_output_dir(o) for o in all_outputs))
            check: dict[str, Any] = {
                "name": _GROUP_DISPLAY_NAMES.get(stage.display_group, stage.display_group),
                "path": dirs[0] if dirs else f"results/{stage.display_group}",
                "paths": dirs if dirs else [f"results/{stage.display_group}"],
                "key_suffixes": suffixes,
            }
            if stage.display_group == "dl_variant_scores":
                check["read_dl_summaries"] = True
            checks.append(check)
            continue

        # Regular stage → one display entry
        suffixes = [_output_suffix(o) for o in stage.outputs]
        dirs = list(dict.fromkeys(_output_dir(o) for o in stage.outputs))
        check = {
            "name": _STAGE_DISPLAY_NAMES.get(name, name.replace("_", " ").title()),
            "path": dirs[0] if dirs else f"results/{name}",
            "key_suffixes": suffixes,
        }
        if stage.summary_file:
            sf = stage.summary_file.replace("{SAMPLE}", SAMPLE_ID)
            check["summary_file"] = sf.rsplit("/", 1)[-1]
        checks.append(check)

    checks.extend(EXTRA_CHECKS)
    return checks


def _build_local_result_dirs() -> list[tuple[str, Path, list[str]]]:
    """Derive local result directory list from STAGES.

    Returns (label, dirpath, key_filenames) tuples.  When multiple stages
    share a directory (e.g. ancestry_admixture → results/ancestry/), each
    stage gets its own entry with its specific output filenames so the
    display can check per-stage completion instead of just directory existence.
    """
    result: list[tuple[str, Path, list[str]]] = []
    seen_groups: set[str] = set()
    # Track (dir, label) pairs already added to avoid exact duplicates,
    # but allow the same dir with different key files.
    seen_entries: set[tuple[str, str]] = set()

    for name in topological_sort(STAGES):
        stage = STAGES[name]

        if stage.display_group:
            if stage.display_group in seen_groups:
                continue
            seen_groups.add(stage.display_group)
            group_stages = [s for s in STAGES.values() if s.display_group == stage.display_group]
            all_outputs = []
            for gs in group_stages:
                all_outputs.extend(gs.outputs)
            key_files = [o.rsplit("/", 1)[-1].replace("{SAMPLE}", SAMPLE_ID) for o in all_outputs]
            dirs = list(dict.fromkeys(_local_subdir(o) for o in all_outputs))
            subdir = dirs[0] if dirs else stage.display_group
            label = _GROUP_DISPLAY_NAMES.get(stage.display_group, stage.display_group)
            entry_key = (subdir, label)
            if entry_key not in seen_entries:
                seen_entries.add(entry_key)
                result.append((label, LOCAL_ANALYSIS / subdir, key_files))
            continue

        # Regular stage — use its specific output filenames as key files
        key_files = [o.rsplit("/", 1)[-1].replace("{SAMPLE}", SAMPLE_ID) for o in stage.outputs]
        dirs = list(dict.fromkeys(_local_subdir(o) for o in stage.outputs))
        subdir = dirs[0] if dirs else name
        label = _STAGE_DISPLAY_NAMES.get(name, name.replace("_", " ").title())
        entry_key = (subdir, label)
        if entry_key not in seen_entries:
            seen_entries.add(entry_key)
            result.append((label, LOCAL_ANALYSIS / subdir, key_files))

    # Non-stage local dirs
    for extra in EXTRA_CHECKS:
        subdir = extra["path"].removeprefix("results/")
        label = extra["name"]
        entry_key = (subdir, label)
        if entry_key not in seen_entries:
            seen_entries.add(entry_key)
            key_files_extra = extra.get("key_suffixes", [])
            result.append((label, LOCAL_ANALYSIS / subdir, key_files_extra))

    for label, dirpath in EXTRA_LOCAL_DIRS:
        result.append((label, dirpath, []))
    return result


VOLUME_CHECKS = _build_volume_checks()
_SDK_RECEIPT_STAGE_LIMIT = 20


def _volume_relative_path(path: str | Path) -> str:
    path_text = str(path)
    if path_text in {DATA_DIR, DATA_DIR.rstrip("/"), "/data", ""}:
        return ""
    if path_text.startswith(f"{DATA_DIR.rstrip('/')}/"):
        return path_text[len(DATA_DIR.rstrip("/")) + 1 :]
    return path_text.lstrip("/")


def _entry_name(entry: Any) -> str:
    return Path(str(getattr(entry, "path", "")).rstrip("/")).name


def _entry_is_dir(entry: Any) -> bool:
    entry_type = getattr(entry, "type", None)
    if entry_type is None:
        return False
    entry_name = getattr(entry_type, "name", None)
    if isinstance(entry_name, str):
        return entry_name.upper() == "DIRECTORY"
    entry_value = getattr(entry_type, "value", None)
    if entry_value is not None:
        return entry_value == 2
    return entry_type == 2 or "DIRECTORY" in str(entry_type).upper()


def _volume_listdir(volume: Any, path: str | Path, *, recursive: bool = False) -> list[Any]:
    relative_path = _volume_relative_path(path)
    try:
        return list(volume.listdir(relative_path, recursive=recursive))
    except TypeError:
        return list(volume.listdir(relative_path))
    except modal.exception.NotFoundError:
        return []


def _volume_read_json(volume: Any, path: str | Path) -> dict[str, Any] | None:
    relative_path = _volume_relative_path(path)
    try:
        payload = b"".join(volume.read_file(relative_path))
    except modal.exception.NotFoundError:
        return None
    if not payload:
        return None
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def _volume_read_text(volume: Any, path: str | Path) -> str | None:
    relative_path = _volume_relative_path(path)
    try:
        payload = b"".join(volume.read_file(relative_path))
    except modal.exception.NotFoundError:
        return None
    if not payload:
        return ""
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _tail_jsonl_lines(payload: str, *, max_lines: int = 5) -> tuple[int, list[dict[str, Any]]]:
    total_entries = 0
    recent_lines: deque[str] = deque(maxlen=max_lines)
    for line in payload.splitlines():
        if not line.strip():
            continue
        total_entries += 1
        recent_lines.append(line)
    recent: list[dict[str, Any]] = []
    for line in recent_lines:
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            recent.append(decoded)
    return total_entries, recent


def _probe_volume_sdk_impl(volume: Any, volume_checks: list[dict[str, Any]], sample_id: str) -> dict:
    result: dict[str, Any] = {}

    def _group_by_parent(entries: list[Any]) -> dict[str, list[Any]]:
        grouped: dict[str, list[Any]] = {}
        for entry in entries:
            parent = str(Path(str(getattr(entry, "path", ""))).parent).rstrip(".")
            grouped.setdefault(parent, []).append(entry)
        return grouped

    result_entries = _volume_listdir(volume, "results", recursive=True)
    runtime_root = _volume_relative_path(canonical_status_root(data_dir=DATA_DIR))
    runtime_entries = _volume_listdir(volume, runtime_root, recursive=True)
    input_entries = _volume_listdir(volume, "input", recursive=False)
    reference_entries = _volume_listdir(volume, "reference", recursive=False)
    log_entries = _volume_listdir(volume, "logs", recursive=False)
    current_log_entries = _volume_listdir(volume, "logs/current", recursive=True)

    grouped_results = _group_by_parent(result_entries)
    grouped_runtime = _group_by_parent(runtime_entries)
    grouped_current_logs = _group_by_parent(current_log_entries)

    for check in volume_checks:
        stage_paths = [_volume_relative_path(rel_path) for rel_path in check.get("paths", [check["path"]])]
        stage_info: dict[str, Any] = {
            "exists": False,
            "files": [],
            "checkpoints": [],
            "summary": None,
        }

        for stage_path in stage_paths:
            if stage_path == "input":
                entries = input_entries
            elif stage_path == "reference":
                entries = reference_entries
            else:
                entries = grouped_results.get(stage_path, [])
            if entries:
                stage_info["exists"] = True
            for entry in sorted(entries, key=lambda item: getattr(item, "path", "")):
                if _entry_is_dir(entry):
                    continue
                info = {
                    "name": _entry_name(entry),
                    "size": getattr(entry, "size", 0),
                    "dir": Path(stage_path).name,
                }
                stage_info["files"].append(info)
        result[check["name"]] = stage_info

    stage_entries = [
        entry
        for entry in grouped_runtime.get(runtime_root, [])
        if _entry_is_dir(entry) and _entry_name(entry) != "state"
    ]

    worker_receipts: list[dict[str, Any]] = []
    runtime_progress: list[dict[str, Any]] = []

    recent_stage_entries = sorted(
        stage_entries,
        key=lambda item: (getattr(item, "mtime", 0), getattr(item, "path", "")),
        reverse=True,
    )[:_SDK_RECEIPT_STAGE_LIMIT]

    for stage_entry in recent_stage_entries:
        stage_root = str(getattr(stage_entry, "path", "")).rstrip("/")

        attempt_entries = [
            entry
            for entry in grouped_runtime.get(f"{stage_root}/attempts", [])
            if _entry_is_dir(entry)
        ]
        if attempt_entries:
            receipt_candidates: list[dict[str, Any]] = []
            for attempt_entry in attempt_entries:
                receipt_payload = _volume_read_json(volume, f"{attempt_entry.path}/receipt.json")
                if receipt_payload is None:
                    continue
                progress_payload = receipt_payload.get("progress", {})
                receipt_candidates.append(
                    {
                        "receipt": receipt_payload,
                        "progress": progress_payload,
                        "updated_at": _worker_updated_at(receipt_payload, progress_payload),
                        "path": str(getattr(attempt_entry, "path", "")),
                    }
                )
            latest_payload = max(
                receipt_candidates,
                key=lambda item: (
                    _parse_timestamp(str(item.get("updated_at", "") or ""))
                    or datetime.min.replace(tzinfo=UTC),
                    str(item.get("path", "")),
                ),
                default=None,
            )
            receipt_payload = latest_payload.get("receipt") if latest_payload else None
            if receipt_payload is not None and (
                not receipt_payload.get("sample_id") or receipt_payload.get("sample_id") == sample_id
            ):
                progress_payload = receipt_payload.get("progress", {})
                worker_receipts.append(
                    {
                        "sample_id": receipt_payload.get("sample_id", ""),
                        "sample_source": receipt_payload.get("sample_source", ""),
                        "stage": receipt_payload.get("stage", _entry_name(stage_entry)),
                        "status": receipt_payload.get("status", ""),
                        "elapsed_s": receipt_payload.get("duration_sec"),
                        "planned_duration_estimate_min": receipt_payload.get("planned_duration_estimate_min"),
                        "planned_resource_class": receipt_payload.get("planned_resource_class", ""),
                        "applicability_policy": receipt_payload.get("applicability_policy", ""),
                        "applicability_trust_class": receipt_payload.get("applicability_trust_class", ""),
                        "applicability_reason": receipt_payload.get("applicability_reason", ""),
                        "updated_at": _worker_updated_at(receipt_payload, progress_payload),
                        "run_id": receipt_payload.get("run_id", ""),
                        "progress": progress_payload,
                    }
                )

        for entry in grouped_runtime.get(stage_root, []):
            if _entry_is_dir(entry):
                continue
            entry_name = _entry_name(entry)
            if not (entry_name.endswith(".progress.json") or entry_name.endswith("_progress.json")):
                continue
            payload = _volume_read_json(volume, entry.path)
            if payload is None:
                runtime_progress.append({"path": stage_root + "/" + entry_name, "payload": {}})
                continue
            payload_status = str(payload.get("status", "")).lower()
            if payload_status in {"done", "success"}:
                continue
            snapshot = coerce_snapshot(payload)
            if snapshot is not None and snapshot.state == "success":
                continue
            runtime_progress.append({"path": str(entry.path), "payload": payload})

    result["_worker_receipts"] = worker_receipts
    result["_runtime_progress"] = runtime_progress

    logs_info: dict[str, Any] = {"exists": False, "scripts": {}}
    current_root = "logs/current"
    current_entries = [entry for entry in grouped_current_logs.get(current_root, []) if _entry_is_dir(entry)]
    if current_entries:
        logs_info["exists"] = True
    preferred_run_ids = _running_receipt_run_ids(worker_receipts)
    interesting_scripts = {
        str(row.get("stage", "")).strip()
        for row in worker_receipts
        if str(row.get("status", "")).lower() == "running"
    }
    interesting_scripts.update(
        str(row.get("payload", {}).get("stage", "")).strip()
        for row in runtime_progress
        if isinstance(row.get("payload"), dict)
    )
    for script_entry in sorted(current_entries, key=lambda item: getattr(item, "path", "")):
        script_name = _entry_name(script_entry)
        if interesting_scripts and script_name not in interesting_scripts:
            continue
        script_root = str(getattr(script_entry, "path", "")).rstrip("/")
        preferred_run_id = preferred_run_ids.get(script_name, "")
        current_payload = (
            _volume_read_json(volume, f"{script_root}/{preferred_run_id}.json")
            if preferred_run_id
            else None
        )
        latest_payload = _volume_read_json(volume, f"{script_root}/latest.json") or {}
        run_id = str(latest_payload.get("run_id", "")).strip()
        if current_payload is None:
            current_payload = _volume_read_json(volume, f"{script_root}/{run_id}.json") if run_id else None
        if current_payload is None:
            for entry in sorted(grouped_current_logs.get(script_root, []), key=lambda item: getattr(item, "path", "")):
                if _entry_is_dir(entry) or _entry_name(entry) == "latest.json":
                    continue
                if not _entry_name(entry).endswith(".json"):
                    continue
                current_payload = _volume_read_json(volume, entry.path)
                if current_payload is not None:
                    break
        log_file_entry = next(
            (
                entry
                for entry in log_entries
                if not _entry_is_dir(entry) and _entry_name(entry) == f"{script_name}.jsonl"
            ),
            None,
        )
        total_entries = 0
        recent_entries: list[dict[str, Any]] = []
        log_size = 0
        if log_file_entry is not None:
            log_size = int(getattr(log_file_entry, "size", 0) or 0)
            log_payload = _volume_read_text(volume, getattr(log_file_entry, "path", ""))
            if log_payload is not None:
                total_entries, recent_entries = _tail_jsonl_lines(log_payload)
        logs_info["scripts"][script_name] = {
            "total_entries": total_entries,
            "size": log_size,
            "recent": recent_entries,
            "current": current_payload,
        }
    result["_pipeline_logs"] = logs_info
    return result

LOCAL_CHECKS = [
    ("Variant-only VCF", _LOCAL_PATHS.deepvariant_vcf),
    ("VCF index", Path(f"{_LOCAL_PATHS.deepvariant_vcf}.tbi")),
    ("CRAM", _LOCAL_PATHS.cram),
    ("CRAM index", Path(f"{_LOCAL_PATHS.cram}.crai")),
]

LOCAL_RESULT_DIRS = _build_local_result_dirs()

# Directories used by multiple stages — need key-file checking to distinguish.
_dir_counts: dict[Path, int] = {}
for _, dirpath, _ in LOCAL_RESULT_DIRS:
    _dir_counts[dirpath] = _dir_counts.get(dirpath, 0) + 1
_shared_dirs: set[Path] = {d for d, c in _dir_counts.items() if c > 1}


# ── Modal probe function (runs remotely, single call) ─────────────────────
# probe_volume logic lives here; Modal wrapper built lazily by _run_volume_probe().


def _probe_volume_impl(volume_checks, data_dir, sample_id) -> dict:
    """Scan entire results directory in one shot. Returns structured status.

    Pure function — no module-level Modal dependency.
    """
    result = {}

    for check in volume_checks:
        stage_paths = [Path(data_dir) / rel_path for rel_path in check.get("paths", [check["path"]])]
        stage_info: dict[str, Any] = {
            "exists": any(stage_path.exists() for stage_path in stage_paths),
            "files": [],
            "checkpoints": [],
            "summary": None,
        }

        dl_summaries = {}
        for stage_path in stage_paths:
            if not stage_path.exists() or not stage_path.is_dir():
                continue
            for f in sorted(stage_path.iterdir()):
                if f.is_file():
                    info = {"name": f.name, "size": f.stat().st_size, "dir": stage_path.name}
                    stage_info["files"].append(info)

            summary_name = check.get("summary_file")
            if summary_name and stage_info["summary"] is None:
                summary_path = stage_path / summary_name
                if summary_path.exists():
                    try:
                        stage_info["summary"] = json.loads(summary_path.read_text())
                    except Exception:
                        stage_info["summary"] = {"error": "parse failed"}

            if check.get("read_dl_summaries"):
                for f in sorted(stage_path.iterdir()):
                    if f.is_file() and f.name.endswith("_summary.json"):
                        try:
                            dl_summaries[f.name] = json.loads(f.read_text())
                        except Exception:
                            dl_summaries[f.name] = {"error": "parse failed"}
        if dl_summaries:
            stage_info["dl_summaries"] = dl_summaries

        result[check["name"]] = stage_info

    # ── Derived worker receipt mirrors (debug only, not control-plane truth) ──
    worker_receipts = []
    status_dir = canonical_status_root(data_dir=data_dir)
    if status_dir.exists() and status_dir.is_dir():
        from pipeline_core import load_stage_run

        for stage_dir in sorted(status_dir.iterdir()):
            stage_name = stage_dir.name
            if not stage_dir.is_dir() or stage_name == "state":
                continue
            attempts_root = stage_dir / "attempts"
            receipt_candidates = sorted(
                attempts_root.glob("*/receipt.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            ) if attempts_root.exists() else []
            if not receipt_candidates:
                continue
            run = load_stage_run(receipt_candidates[0])
            if run is None:
                continue
            if run.sample_id and run.sample_id != sample_id:
                continue
            progress_payload = run.progress
            worker_receipts.append(
                {
                    "sample_id": run.sample_id,
                    "sample_source": run.sample_source,
                    "stage": run.stage,
                    "status": run.status,
                    "elapsed_s": run.duration_sec,
                    "planned_duration_estimate_min": run.planned_duration_estimate_min,
                    "planned_resource_class": run.planned_resource_class,
                    "applicability_policy": run.applicability_policy,
                    "applicability_trust_class": run.applicability_trust_class,
                    "applicability_reason": run.applicability_reason,
                    "updated_at": _worker_updated_at(run, progress_payload),
                    "run_id": run.run_id,
                    "progress": progress_payload,
                }
            )
    result["_worker_receipts"] = worker_receipts

    runtime_progress = []
    if status_dir.exists() and status_dir.is_dir():
        progress_candidates = {
            *status_dir.glob("*/*.progress.json"),
            *status_dir.glob("*/*_progress.json"),
        }
        for progress_path in sorted(progress_candidates):
            try:
                payload = json.loads(progress_path.read_text())
            except (OSError, json.JSONDecodeError):
                runtime_progress.append({"path": str(progress_path), "payload": {}})
                continue
            payload_status = str(payload.get("status", "")).lower() if isinstance(payload, dict) else ""
            if payload_status in {"done", "success"}:
                continue
            snapshot = coerce_snapshot(payload)
            if snapshot is not None and snapshot.state == "success":
                continue
            runtime_progress.append({"path": str(progress_path), "payload": payload})
    result["_runtime_progress"] = runtime_progress

    # ── Read pipeline logs from /data/logs/ ──
    logs_dir = Path(data_dir) / "logs"
    current_dir = logs_dir / "current"
    logs_info: dict[str, Any] = {"exists": logs_dir.exists(), "scripts": {}}
    current_payloads: dict[str, dict[str, Any]] = {}
    preferred_run_ids = _running_receipt_run_ids(worker_receipts)
    if current_dir.exists() and current_dir.is_dir():
        for script_dir in sorted(current_dir.iterdir()):
            if not script_dir.is_dir():
                continue
            try:
                snapshot_path = None
                preferred_run_id = preferred_run_ids.get(script_dir.name, "")
                if preferred_run_id:
                    candidate = script_dir / f"{preferred_run_id}.json"
                    if candidate.exists():
                        snapshot_path = candidate
                latest_path = script_dir / "latest.json"
                if snapshot_path is None and latest_path.exists():
                    latest_payload = json.loads(latest_path.read_text())
                    run_id = str(latest_payload.get("run_id", "")).strip()
                    if run_id:
                        candidate = script_dir / f"{run_id}.json"
                        if candidate.exists():
                            snapshot_path = candidate
                if snapshot_path is None:
                    candidates = sorted(
                        path for path in script_dir.glob("*.json") if path.name != "latest.json"
                    )
                    if candidates:
                        snapshot_path = candidates[-1]
                if snapshot_path is None:
                    continue
                current_payloads[script_dir.name] = json.loads(snapshot_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
        for snapshot_path in sorted(current_dir.glob("*.json")):
            try:
                current_payloads.setdefault(snapshot_path.stem, json.loads(snapshot_path.read_text()))
            except (OSError, json.JSONDecodeError):
                continue
    if logs_dir.exists() and logs_dir.is_dir():
        from collections import deque

        for f in sorted(logs_dir.iterdir()):
            if f.is_file() and f.name.endswith(".jsonl"):
                script = f.name.replace(".jsonl", "")
                file_size = f.stat().st_size
                recent = []
                total_entries = 0
                try:
                    with open(f) as fh:
                        tail = deque(maxlen=5)
                        for line in fh:
                            total_entries += 1
                            tail.append(line)
                    for line in tail:
                        try:
                            recent.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            pass
                except OSError:
                    pass
                logs_info["scripts"][script] = {
                    "total_entries": total_entries,
                    "size": file_size,
                    "recent": recent,
                    "current": current_payloads.get(script),
                }
    for script, current in current_payloads.items():
        logs_info["scripts"].setdefault(
            script,
            {
                "total_entries": 0,
                "size": 0,
                "recent": [],
                "current": current,
            },
        )
    result["_pipeline_logs"] = logs_info

    return result


@app.function(image=image, volumes={DATA_DIR: vol}, timeout=120, memory=256)
def probe_volume() -> str:
    vol.reload()
    return json.dumps(_probe_volume_impl(VOLUME_CHECKS, DATA_DIR, SAMPLE_ID))


def _run_volume_probe() -> dict:
    """Probe the Modal volume via SDK, falling back to the remote helper if needed."""
    try:
        try:
            vol.reload()
        except RuntimeError as exc:
            if "reload() can only be called from within a running function" not in str(exc):
                raise
        return _probe_volume_sdk_impl(vol, VOLUME_CHECKS, SAMPLE_ID)
    except Exception:
        with app.run():
            result = probe_volume.remote()
        if result is None:
            raise RuntimeError("Modal volume probe returned None")
        if not isinstance(result, str):
            raise RuntimeError(f"Modal volume probe returned {type(result).__name__}, expected JSON string")
        parsed = json.loads(result)
        if not isinstance(parsed, dict):
            raise RuntimeError(
                f"Modal volume probe decoded to {type(parsed).__name__}, expected dict"
            )
        return parsed


# fmt_size imported from variant_evidence_core


# ── Volume display ────────────────────────────────────────────────────────


def show_volume(probe_data: dict) -> None:
    print("=" * 62)
    print("  MODAL VOLUME STATUS")
    print("=" * 62)
    print()

    for check in VOLUME_CHECKS:
        name = check["name"]
        info = probe_data.get(name, {})

        if not info.get("exists"):
            missing_paths = check.get("paths", [check["path"]])
            print(f"  [ ]  {name}")
            print(f"       {', '.join(missing_paths)}/ — not found")
            print()
            continue

        files = info.get("files", [])
        total = sum(f["size"] for f in files)

        # Match key suffixes
        key_suffixes = check["key_suffixes"]
        found_keys = []
        missing_keys = []
        for suffix in key_suffixes:
            matches = [f for f in files if f["name"].endswith(suffix)]
            if matches:
                found_keys.extend(matches)
            else:
                missing_keys.append(suffix)

        icon = "[x]" if not missing_keys else "[~]" if found_keys else "[ ]"
        print(f"  {icon}  {name}  ({fmt_size(total)}, {len(files)} files)")

        for kf in found_keys[:5]:
            print(f"       + {kf['name']} ({fmt_size(kf['size'])})")
        if len(found_keys) > 5:
            print(f"       + ... and {len(found_keys) - 5} more")

        for mk in missing_keys:
            print(f"       - MISSING: *{mk}")

        # Show summary highlights
        summary = info.get("summary")
        if summary and (not isinstance(summary, dict) or not summary.get("error")):
            if name == "Local ancestry" and summary.get("status") == "skipped":
                missing_keys = [
                    mk for mk in missing_keys if not mk.endswith("local_ancestry_segments.tsv.gz")
                ]
            _print_summary_highlights(name, summary)

        # Show DL variant score summaries (special case)
        dl_summaries = info.get("dl_summaries")
        if dl_summaries:
            _print_dl_score_highlights(dl_summaries, files)

        print()


def _show_runtime_progress(
    progress_rows: list[dict[str, Any]],
    worker_receipts: list[dict[str, Any]] | None = None,
) -> None:
    if not progress_rows:
        return

    latest_receipts = _latest_receipts_by_stage(worker_receipts or [])
    visible_rows: list[dict[str, Any]] = []
    for row in progress_rows:
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        stage = _runtime_row_stage(row)
        if stage and _progress_predates_receipt(payload, latest_receipts.get(stage)):
            continue
        visible_rows.append(row)

    if not visible_rows:
        return

    print("=" * 62)
    print("  RUNTIME PROGRESS (VOLUME)")
    print("=" * 62)
    print()

    for row in visible_rows:
        progress_path = row.get("path", "")
        payload = row.get("payload", {})
        if not payload:
            print(f"  [!] {progress_path}")
            continue

        summary = _format_progress_suffix(payload) or payload.get("message") or payload.get("status", "")
        print(f"  [>] {progress_path} {summary}".rstrip())

        details: dict[str, Any] = {}
        if isinstance(payload, dict):
            nested_details = payload.get("details")
            if isinstance(nested_details, dict):
                details.update(nested_details)
            details.update(payload)
        detail_parts: list[str] = []
        for key in (
            "elapsed_s",
            "index_file_count",
            "index_total_gb",
            "annotation_files",
            "annotation_mb",
            "temp_h5_mb",
            "lines",
            "output_vcf_mb",
        ):
            value = details.get(key)
            if value in (None, "", 0, 0.0):
                continue
            detail_parts.append(f"{key}={value}")
        if detail_parts:
            print(f"       >> {' | '.join(detail_parts)}")
        for key in ("checkpoint_label", "cmd", "stdout_tail", "stderr_tail"):
            value = str(details.get(key, "") or "").strip()
            if not value:
                continue
            compact = " ".join(value.split())
            if len(compact) > 180:
                compact = compact[:177] + "..."
            print(f"       >> {key}: {compact}")
        budget_suffix = _runtime_budget_suffix(
            str(payload.get("stage", "") or ""),
            progress_payload=payload,
            updated_at=str(payload.get("updated_at", "") or ""),
        )
        if budget_suffix:
            print(f"       >> {budget_suffix}")
    print()


def _running_receipt_run_ids(
    worker_receipts: list[dict[str, Any]],
) -> dict[str, str]:
    run_ids: dict[str, str] = {}
    for row in worker_receipts:
        if str(row.get("status", "")).lower() != "running":
            continue
        stage = str(row.get("stage", "") or "").strip()
        run_id = str(row.get("run_id", "") or "").strip()
        if stage and run_id:
            run_ids[stage] = run_id
    return run_ids


def _latest_receipts_by_stage(
    worker_receipts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest_receipt_by_stage: dict[str, dict[str, Any]] = {}
    for row in worker_receipts:
        stage = str(row.get("stage", "") or "").strip()
        if not stage:
            continue
        current = latest_receipt_by_stage.get(stage)
        row_ts = _parse_timestamp(str(row.get("updated_at", "") or ""))
        current_ts = _parse_timestamp(str(current.get("updated_at", "") or "")) if current else None
        if current is None or (row_ts and (current_ts is None or row_ts >= current_ts)):
            latest_receipt_by_stage[stage] = row
    return latest_receipt_by_stage


def _progress_predates_receipt(payload: dict[str, Any], receipt_row: dict[str, Any] | None) -> bool:
    if not receipt_row:
        return False
    progress_updated_at = _parse_timestamp(str(payload.get("updated_at", "") or ""))
    if progress_updated_at is None:
        return False
    receipt_progress = receipt_row.get("progress", {}) if isinstance(receipt_row.get("progress"), dict) else {}
    receipt_started_at = _parse_timestamp(str(receipt_progress.get("started_at", "") or ""))
    if receipt_started_at is None:
        return False
    return progress_updated_at < receipt_started_at


def _runtime_row_stage(row: dict[str, Any]) -> str:
    payload = row.get("payload", {}) if isinstance(row, dict) else {}
    if isinstance(payload, dict):
        stage = str(payload.get("stage", "") or payload.get("script", "")).strip()
        if stage:
            return stage
    raw_path = str(row.get("path", "") or "")
    return Path(raw_path).parent.name if raw_path else ""


def _runtime_row_updated_at(row: dict[str, Any]) -> str:
    payload = row.get("payload", {}) if isinstance(row, dict) else {}
    if isinstance(payload, dict):
        updated_at = str(payload.get("updated_at", "") or "")
        if updated_at:
            return updated_at
    return ""


def _prefer_runtime_row(candidate: dict[str, Any], current: dict[str, Any] | None) -> bool:
    if current is None:
        return True
    candidate_payload = candidate.get("payload", {}) if isinstance(candidate, dict) else {}
    current_payload = current.get("payload", {}) if isinstance(current, dict) else {}
    if not isinstance(candidate_payload, dict):
        candidate_payload = {}
    if not isinstance(current_payload, dict):
        current_payload = {}
    current_has_signal = any(
        str(current_payload.get(key, "") or "").strip() for key in ("step", "message", "stdout_tail")
    )
    candidate_has_signal = any(
        str(candidate_payload.get(key, "") or "").strip() for key in ("step", "message", "stdout_tail")
    )
    if candidate_has_signal and not current_has_signal:
        return True
    if current_has_signal and not candidate_has_signal:
        return False
    candidate_ts = _parse_timestamp(_runtime_row_updated_at(candidate))
    current_ts = _parse_timestamp(_runtime_row_updated_at(current))
    if candidate_ts and current_ts:
        return candidate_ts >= current_ts
    if candidate_ts and not current_ts:
        return True
    return False


def _active_runtime_rows_by_stage(
    progress_rows: list[dict[str, Any]],
    worker_receipts: list[dict[str, Any]],
    pipeline_logs: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows_by_stage: dict[str, dict[str, Any]] = {}
    latest_receipt_by_stage = _latest_receipts_by_stage(worker_receipts)

    for row in progress_rows:
        stage = _runtime_row_stage(row)
        if not stage:
            continue
        latest_receipt = latest_receipt_by_stage.get(stage)
        if latest_receipt and str(latest_receipt.get("status", "")).lower() != "running":
            continue
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        payload_state = str(payload.get("state", "") or payload.get("status", "")).lower()
        if payload_state in {"failed", "error"}:
            continue
        if _progress_predates_receipt(payload, latest_receipt):
            continue
        candidate = {
            "stage": stage,
            "source": "progress",
            "payload": payload,
            "updated_at": _runtime_row_updated_at(row),
        }
        if _prefer_runtime_row(candidate, rows_by_stage.get(stage)):
            rows_by_stage[stage] = candidate

    for row in worker_receipts:
        if str(row.get("status", "")).lower() != "running":
            continue
        stage = str(row.get("stage", "") or "").strip()
        if not stage:
            continue
        candidate = {
            "stage": stage,
            "source": "receipt",
            "payload": row.get("progress", {}) if isinstance(row.get("progress"), dict) else {},
            "updated_at": str(row.get("updated_at", "") or ""),
            "planned_duration_estimate_min": row.get("planned_duration_estimate_min"),
            "fallback_elapsed_s": row.get("elapsed_s"),
        }
        if _prefer_runtime_row(candidate, rows_by_stage.get(stage)):
            rows_by_stage[stage] = candidate

    scripts = pipeline_logs.get("scripts", {}) if isinstance(pipeline_logs, dict) else {}
    for script, info in scripts.items():
        if not isinstance(info, dict):
            continue
        current = info.get("current", {})
        if not isinstance(current, dict):
            continue
        current_state = str(current.get("state", "") or "").lower()
        if current_state not in {"", "running"}:
            continue
        current_script = str(current.get("script", "") or script).strip()
        stage = str(current.get("stage", "") or current_script or script).strip()
        if current_script in latest_receipt_by_stage:
            stage = current_script
        if not stage:
            continue
        latest_receipt = latest_receipt_by_stage.get(stage)
        if latest_receipt and str(latest_receipt.get("status", "")).lower() != "running":
            continue
        candidate = {
            "stage": stage,
            "source": "log",
            "payload": current,
            "updated_at": str(current.get("updated_at", "") or ""),
        }
        if _prefer_runtime_row(candidate, rows_by_stage.get(stage)):
            rows_by_stage[stage] = candidate

    return rows_by_stage


def _show_active_runtime(
    progress_rows: list[dict[str, Any]],
    worker_receipts: list[dict[str, Any]],
    pipeline_logs: dict[str, Any],
) -> None:
    rows_by_stage = _active_runtime_rows_by_stage(progress_rows, worker_receipts, pipeline_logs)
    if not rows_by_stage:
        return

    print("=" * 62)
    print("  ACTIVE RUNTIME")
    print("=" * 62)
    print()

    ordered_rows = sorted(
        rows_by_stage.values(),
        key=lambda row: (
            _parse_timestamp(str(row.get("updated_at", "") or "")) or datetime.min.replace(tzinfo=UTC),
            str(row.get("stage", "")),
        ),
        reverse=True,
    )
    for row in ordered_rows:
        stage = str(row.get("stage", "") or "?")
        source = str(row.get("source", "") or "")
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        progress_suffix = _format_progress_suffix(payload) or str(payload.get("message", "") or "").strip()
        print(f"  {stage:35s} [{source}] {progress_suffix}".rstrip())
        budget_suffix = _runtime_budget_suffix(
            stage,
            progress_payload=payload,
            updated_at=str(row.get("updated_at", "") or ""),
            fallback_elapsed_s=row.get("fallback_elapsed_s"),
            planned_duration_estimate_min=row.get("planned_duration_estimate_min"),
        )
        if budget_suffix:
            print(f"       >> {budget_suffix}")
    print()


def _local_bridge_state_for_stage(stage_name: str) -> dict[str, Any]:
    stage = STAGES.get(stage_name)
    if stage is None or not stage.outputs:
        return {"available": False, "detail": "no local bridge spec"}

    stage_dirs = [LOCAL_ANALYSIS / _local_subdir(output) for output in stage.outputs]
    stage_dirs = list(dict.fromkeys(stage_dirs))
    key_files = [output.rsplit("/", 1)[-1].replace("{SAMPLE}", SAMPLE_ID) for output in stage.outputs]

    existing_dirs = [dirpath for dirpath in stage_dirs if dirpath.exists()]
    if not existing_dirs:
        return {"available": False, "detail": "local dir missing"}

    found_files: list[Path] = []
    for dirpath in existing_dirs:
        if dirpath in _shared_dirs and key_files:
            found_files.extend(dirpath / key_file for key_file in key_files if (dirpath / key_file).exists())
        else:
            found_files.extend(path for path in dirpath.iterdir() if path.is_file())

    if found_files:
        return {
            "available": True,
            "detail": f"{len(found_files)} local file(s)",
        }
    return {"available": False, "detail": "local files missing"}


def _reconcile_stage_rows(
    control_plane_rows: list[dict[str, Any]],
    worker_receipts: list[dict[str, Any]],
    progress_rows: list[dict[str, Any]],
    pipeline_logs: dict[str, Any],
    *,
    local_bridge_state: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    latest_receipt_by_stage = _latest_receipts_by_stage(worker_receipts)
    active_runtime_by_stage = _active_runtime_rows_by_stage(progress_rows, worker_receipts, pipeline_logs)
    control_plane_by_stage = {
        str(row.get("stage", "") or "").strip(): row
        for row in control_plane_rows
        if str(row.get("stage", "") or "").strip()
    }
    stage_names = set(control_plane_by_stage) | set(latest_receipt_by_stage) | set(active_runtime_by_stage)
    local_state_by_stage = local_bridge_state or {
        stage_name: _local_bridge_state_for_stage(stage_name) for stage_name in stage_names
    }

    reconciled_rows: list[dict[str, str]] = []
    for stage_name in sorted(stage_names):
        control_plane_row = control_plane_by_stage.get(stage_name, {})
        receipt_row = latest_receipt_by_stage.get(stage_name, {})
        active_runtime_row = active_runtime_by_stage.get(stage_name, {})
        local_state = local_state_by_stage.get(stage_name, {"available": False, "detail": "local state unknown"})

        control_plane_status = str(control_plane_row.get("status", "") or "").lower()
        receipt_status = str(receipt_row.get("status", "") or "").lower()
        runtime_source = str(active_runtime_row.get("source", "") or "")
        local_state_label = "ready" if local_state.get("available") else "missing"

        mismatch_class = ""
        detail = ""
        if runtime_source:
            if local_state.get("available"):
                mismatch_class = "local_stale"
                detail = "local bridge exists but a newer run is still active"
            else:
                mismatch_class = "running_signal"
                detail = "runtime evidence says the stage is active now"
        elif receipt_status == "running":
            mismatch_class = "stale_receipt" if control_plane_status != "running" else "incomplete_attempt"
            detail = "latest receipt is still running, but there is no current runtime signal"
        elif control_plane_status == "running":
            mismatch_class = "local_stale" if local_state.get("available") else "incomplete_attempt"
            detail = "control plane expects active work, but no current runtime signal was found"
        elif receipt_status in {"success", "completed", "skipped"}:
            if not local_state.get("available"):
                mismatch_class = "bridge_failed"
                detail = "worker reached a terminal receipt, but local output is missing"
        elif receipt_status == "failed":
            mismatch_class = "local_stale" if local_state.get("available") else "failed_receipt"
            detail = "latest worker receipt is a terminal failure"
        elif control_plane_status in {"failed", "manual", "dataset_blocked"}:
            mismatch_class = "local_stale" if local_state.get("available") else "incomplete_attempt"
            detail = control_plane_row.get("blocker_detail") or "control plane is not in a completed state"
        else:
            continue

        evidence_parts = []
        if control_plane_status:
            evidence_parts.append(f"cp={control_plane_status}")
        if receipt_status:
            evidence_parts.append(f"receipt={receipt_status}")
        if runtime_source:
            evidence_parts.append(f"runtime={runtime_source}")
        evidence_parts.append(f"local={local_state_label}")
        reconciled_rows.append(
            {
                "stage": stage_name,
                "class": mismatch_class,
                "evidence": " ".join(evidence_parts),
                "detail": str(detail),
                "local_detail": str(local_state.get("detail", "") or ""),
            }
        )

    return reconciled_rows


def _show_reconciliation(
    control_plane_rows: list[dict[str, Any]],
    worker_receipts: list[dict[str, Any]],
    progress_rows: list[dict[str, Any]],
    pipeline_logs: dict[str, Any],
) -> None:
    rows = _reconcile_stage_rows(
        control_plane_rows,
        worker_receipts,
        progress_rows,
        pipeline_logs,
    )
    if not rows:
        return

    print("=" * 62)
    print("  RECONCILIATION")
    print("=" * 62)
    print()

    for row in rows:
        print(f"  {row['stage']:35s} {row['class']:18s} {row['evidence']}".rstrip())
        detail = row.get("detail", "")
        if detail:
            print(f"       >> {detail}")
    print()


def _print_summary_highlights(stage_name: str, summary: dict) -> None:
    """Extract and display key facts from summary JSONs."""
    if stage_name == "Haplogroups":
        mt = summary.get("mt_haplogroup", {})
        y = summary.get("y_haplogroup", {})
        tel = summary.get("telomere", {})
        if mt.get("haplogroup"):
            print(f"       > mtDNA: {mt['haplogroup']} (quality {mt.get('quality', '?')})")
        if y.get("haplogroup"):
            print(f"       > Y-chr: {y['haplogroup']} (confidence {y.get('confidence', '?')})")
        tel_content = tel.get("telomere_content")
        if isinstance(tel_content, (int, float)):
            print(f"       > TelomereHunter2 tel_content: {tel_content:.2f}")
        elif tel.get("telomere_length_kb"):
            print(f"       > Telomere: {tel['telomere_length_kb']:.2f} kb")
        elif tel.get("error"):
            err = str(tel["error"])[:80]
            print(f"       > Telomere: FAILED — {err}")
        elif tel.get("status"):
            print(f"       > Telomere: {tel['status']}")

    elif stage_name == "Ancestry PCA":
        superpop = summary.get("weighted_superpop_similarity_weights") or summary.get(
            "weighted_superpop_proportions", {}
        )
        subpop = summary.get("weighted_pop_proportions", {})
        if isinstance(superpop, dict) and superpop:
            top_super = sorted(
                superpop.items(),
                key=lambda item: float(item[1]) if isinstance(item[1], (int, float)) else 0.0,
                reverse=True,
            )[:2]
            top_super_text = ", ".join(
                f"{label} {float(value):.1%}" if isinstance(value, (int, float)) else f"{label} n/a"
                for label, value in top_super
            )
            print(f"       > Global: {top_super_text}")
        if isinstance(subpop, dict) and subpop:
            top_sub = sorted(
                subpop.items(),
                key=lambda item: float(item[1]) if isinstance(item[1], (int, float)) else 0.0,
                reverse=True,
            )[:3]
            top_sub_text = ", ".join(
                f"{label} {float(value):.1%}" if isinstance(value, (int, float)) else f"{label} n/a"
                for label, value in top_sub
            )
            print(f"       > Fine: {top_sub_text}")

    elif stage_name == "Ancestry admixture":
        best_k = summary.get("best_k_unsupervised")
        fit = summary.get("fit_diagnostics", {})
        dominant_component = fit.get("dominant_component")
        dominant_value = fit.get("dominant_component_mean")
        if best_k is not None:
            print(f"       > Best K: {best_k}")
        if dominant_component is not None and isinstance(dominant_value, (int, float)):
            print(f"       > Dominant: {dominant_component} ({float(dominant_value):.1%})")
        stability = fit.get("component_stability_max_sd")
        if isinstance(stability, (int, float)):
            print(f"       > Stability (max SD): {float(stability):.4f}")

    elif stage_name == "Ancestry EUR fine":
        dominant_population = summary.get("dominant_population")
        dominant_mean = summary.get("dominant_population_mean")
        if dominant_population is not None and isinstance(dominant_mean, (int, float)):
            print(
                f"       > Dominant EUR group: {dominant_population} ({float(dominant_mean):.1%})"
            )
        estimates = summary.get("population_estimates", [])
        if isinstance(estimates, list) and estimates:
            top_estimates = sorted(
                [row for row in estimates if isinstance(row, dict)],
                key=lambda row: row.get("mean", 0.0),
                reverse=True,
            )[:3]
            if top_estimates:
                detail_text = ", ".join(
                    f"{row.get('population', '?')} {row.get('mean', 0.0):.1%}"
                    for row in top_estimates
                )
                print(f"       > Top groups: {detail_text}")

    elif stage_name == "Local ancestry":
        status = summary.get("status", "?")
        print(f"       > Status: {status}")
        if status == "skipped":
            reason = str(summary.get("skip_reason", ""))[:120]
            if reason:
                print(f"       > Reason: {reason}")
        elif status == "success":
            engine = summary.get("engine", "?")
            segment_count = summary.get("segment_count", "?")
            print(f"       > Engine: {engine}, segments: {segment_count}")

    elif stage_name == "ExpansionHunter":
        total = summary.get("total_loci", "?")
        flagged = summary.get("flagged_loci", [])
        print(f"       > {total} loci, {len(flagged)} flagged")

    elif stage_name == "DELLY (SVs)":
        by_type = summary.get("by_type", {})
        total = summary.get("total_pass", sum(by_type.values()) if by_type else "?")
        print(
            f"       > {total} pass SVs: {json.dumps(by_type)}"
            if by_type
            else f"       > {total} pass SVs"
        )

    elif stage_name == "Rare-variant triage":
        for key in ("total_variants", "rare_high_moderate", "high_impact_only", "clinvar_flagged"):
            val = summary.get(key)
            if val is not None:
                count = val.get("count", val) if isinstance(val, dict) else val
                print(
                    f"       > {key}: {count:,}"
                    if isinstance(count, (int, float))
                    else f"       > {key}: {count}"
                )

    elif stage_name == "PRS percentile":
        if isinstance(summary, list):
            for row in summary[:5]:
                trait = row.get("trait", "?")
                pct = row.get("percentile_gaussian")
                z_val = row.get("z_score")
                pct_str = f"{pct:.0f}%" if pct is not None else "N/A"
                z_str = f"z={z_val:.2f}" if z_val is not None else ""
                print(f"       > {trait}: {pct_str} ({z_str})")
            if len(summary) > 5:
                print(f"       > ... and {len(summary) - 5} more traits")

    elif stage_name == "CI-SpliceAI":
        n_variants = summary.get("total_variants") or summary.get("variants_scored")
        n_hits = summary.get("hits") or summary.get("significant_hits")
        parts = []
        if n_variants is not None:
            parts.append(f"{n_variants:,} variants scored")
        if n_hits is not None:
            parts.append(f"{n_hits:,} hits")
        if parts:
            print(f"       > {', '.join(parts)}")

    elif stage_name == "Manta SV":
        by_type = summary.get("by_type", {})
        total = (
            summary.get("total_pass") or summary.get("total_svs") or sum(by_type.values())
            if by_type
            else None
        )
        if by_type:
            print(f"       > {total or '?'} pass SVs: {json.dumps(by_type)}")
        elif total:
            print(f"       > {total} SVs")


def _print_dl_score_highlights(dl_summaries: dict, files: list[dict]) -> None:
    """Display DL variant score tool summaries."""
    TOOL_NAMES = {
        "alphamissense_summary.json": "AlphaMissense",
        "gpn_msa_summary.json": "GPN-MSA",
        "alphagenome_summary.json": "AlphaGenome",
        "absplice2_summary.json": "AbSplice2",
        "ncboost2_summary.json": "NCBoost2",
        "evo2_summary.json": "Evo2",
        "spliceai_summary.json": "SpliceAI",
    }

    for fname, data in sorted(dl_summaries.items()):
        tool = TOOL_NAMES.get(fname, fname.replace("_summary.json", ""))
        if data.get("error"):
            print(f"       > {tool}: summary parse failed")
            continue
        scored = (
            data.get("variants_scored") or data.get("total_scored") or data.get("total_variants")
        )
        if scored is not None:
            print(f"       > {tool}: {scored:,} variants scored")
        else:
            print(f"       > {tool}: summary present")

    # Check if merged file exists
    has_merged = any(f["name"] == "merged_dl_scores.tsv" for f in files)
    if has_merged:
        merged_size = next((f["size"] for f in files if f["name"] == "merged_dl_scores.tsv"), 0)
        print(f"       > Merged: merged_dl_scores.tsv ({fmt_size(merged_size)})")
    else:
        print("       - Merged: merged_dl_scores.tsv NOT YET CREATED")


# ── Local display ─────────────────────────────────────────────────────────


def show_local() -> None:
    print("=" * 62)
    print("  LOCAL FILES")
    print("=" * 62)
    print()

    print("  Input:")
    for label, path in LOCAL_CHECKS:
        if path.exists():
            print(f"    [x] {label} ({fmt_size(path.stat().st_size)})")
        else:
            print(f"    [ ] {label}")
    print()

    print("  Downloaded results:")
    for label, dirpath, key_files in LOCAL_RESULT_DIRS:
        if not dirpath.exists():
            print(f"    [ ] {label}")
            continue
        if key_files and dirpath in _shared_dirs:
            # Shared directory: check for stage-specific files
            found = [dirpath / kf for kf in key_files if (dirpath / kf).exists()]
            if not found:
                print(f"    [ ] {label}")
                continue
            total = sum(f.stat().st_size for f in found)
            print(f"    [x] {label} ({len(found)} files, {fmt_size(total)})")
        else:
            # Unique directory: count all files
            files = [f for f in dirpath.iterdir() if f.is_file()]
            if not files:
                print(f"    [ ] {label}")
                continue
            total = sum(f.stat().st_size for f in files)
            print(f"    [x] {label} ({len(files)} files, {fmt_size(total)})")
    print()

    progress_paths: list[Path] = []
    if LOCAL_ANALYSIS.exists():
        progress_paths.extend(sorted(LOCAL_ANALYSIS.rglob("*.progress.json")))
    databases_root = Path("databases")
    if databases_root.exists():
        progress_paths.extend(sorted(databases_root.rglob("*.progress.json")))

    visible_progress: list[tuple[Path, dict[str, Any]]] = []
    for progress_path in progress_paths:
        try:
            payload = json.loads(progress_path.read_text())
        except (OSError, json.JSONDecodeError):
            visible_progress.append((progress_path, {}))
            continue
        snapshot = coerce_snapshot(payload)
        if snapshot is not None and snapshot.state == "success":
            continue
        if snapshot is None and str(payload.get("status", "")).lower() in {"done", "success"}:
            continue
        visible_progress.append((progress_path, payload))

    if visible_progress:
        print("  Local progress:")
        for progress_path, payload in visible_progress:
            if not payload:
                print(f"    [!] {progress_path}")
                continue
            summary = _format_progress_suffix(payload) or payload.get("message") or payload.get("status", "")
            print(f"    [>] {progress_path} {summary}".rstrip())
        print()


# ── Running apps ──────────────────────────────────────────────────────────


def show_apps() -> None:
    print("=" * 62)
    print("  RUNNING MODAL APPS")
    print("=" * 62)
    print()

    try:
        cmd = [sys.executable, "-m", "modal", "app", "list", "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            print(f"  ERROR: {proc.stderr.strip()[:200]}")
            return
        apps = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"  ERROR: {exc}")
        return

    keywords = {
        "cpsr",
        "vep",
        "pharmcat",
        "slivar",
        "delly",
        "expansion",
        "haplogroup",
        "telomere",
        "glimpse",
        "triage",
        "genomic",
        "opencravat",
        "optitype",
        "hla",
        "pgx",
        "mito",
        "prs",
        "roh",
        "annotsv",
        "status",
        "spliceai",
        "absplice",
        "ncboost",
        "evo2",
        "alphagenome",
        "alphamissense",
        "manta",
        "chip",
        "ancestry",
        "gwas",
        "trait",
        "dl-variant",
        "carrier",
        "acmg",
        "qc",
    }

    relevant = []
    for entry in apps:
        desc = str(entry.get("Description", "")).lower()
        app_id = str(entry.get("App ID", "")).lower()
        if any(kw in desc or kw in app_id for kw in keywords):
            relevant.append(entry)

    if not relevant:
        print("  (no genomics apps in recent list)")
    else:
        for entry in relevant[:15]:
            state = entry.get("State", "?")
            arrow = ">>>" if state == "running" else "   "
            print(
                f"  {arrow} {entry.get('Description', '?'):30s}  {state:10s}  "
                f"{entry.get('Created at', '?')}"
            )
    print()


# ── Pipeline logs display ─────────────────────────────────────────────────


def _show_pipeline_logs(logs_info: dict) -> None:
    if not logs_info.get("exists") or not logs_info.get("scripts"):
        return

    print("=" * 62)
    print("  PIPELINE LOGS (/data/logs/)")
    print("=" * 62)
    print()

    for script, info in sorted(logs_info["scripts"].items()):
        total_n = info.get("total_entries", 0)
        recent = info.get("recent", [])
        current = info.get("current")
        last = recent[-1] if recent else {}
        if not last and isinstance(current, dict):
            current_message = str(current.get("message", "") or "").strip()
            current_stage = str(current.get("step") or current.get("stage") or current.get("script") or "")
            current_state = str(current.get("state", "") or "").lower()
            if current_message or current_stage or current_state:
                inferred_level = "HEARTBEAT" if current_state == "running" else current_state.upper() or "SNAPSHOT"
                last = {
                    "ts": current.get("updated_at", "?"),
                    "level": inferred_level,
                    "stage": current_stage or current_message,
                }
        last_ts = last.get("ts", "?")
        last_level = last.get("level", "?")
        last_stage = last.get("stage", last.get("msg", ""))
        progress_suffix = _format_progress_suffix(current)

        if last_ts and last_ts != "?" and "T" in last_ts:
            last_ts = last_ts.split("T")[1][:5] + " UTC"

        icon = (
            "!!"
            if last_level == "ERROR"
            else ">>"
            if last_level in {"PROGRESS", "HEARTBEAT"}
            else "ok"
            if last_level == "DONE"
            else ".."
        )
        print(
            f"  [{icon}] {script:35s} {total_n:4d} entries  "
            f"last: {last_level} {last_stage} ({last_ts})"
        )
        if progress_suffix:
            print(f"       >> {progress_suffix}")
        budget_suffix = _runtime_budget_suffix(
            str(current.get("stage") or current.get("script") or script) if isinstance(current, dict) else script,
            progress_payload=current if isinstance(current, dict) else None,
            updated_at=str(current.get("updated_at", "") or "") if isinstance(current, dict) else "",
        )
        if budget_suffix:
            print(f"       >> {budget_suffix}")

        for entry in recent:
            if entry.get("level") == "ERROR":
                err = entry.get("error", "")[:80]
                print(f"       !! ERROR: {err}")

    print()


def _show_worker_receipts(worker_receipts: list[dict[str, Any]]) -> None:
    if not worker_receipts:
        return

    print("=" * 62)
    print("  WORKER RECEIPTS (VOLUME)")
    print("=" * 62)
    print()

    for row in sorted(worker_receipts, key=lambda item: item.get("stage", "")):
        stage = row.get("stage", "?")
        status = str(row.get("status", "?")).lower()
        updated = str(row.get("updated_at", "") or "")
        progress_suffix = _format_progress_suffix(row.get("progress"))
        ts = updated.split("T")[1][:5] if "T" in updated else ""
        print(f"  {stage:35s} {status:10s} {ts:>5s}  {progress_suffix}".rstrip())
        budget_suffix = _runtime_budget_suffix(
            str(stage),
            progress_payload=row.get("progress"),
            updated_at=updated,
            fallback_elapsed_s=row.get("elapsed_s"),
            planned_duration_estimate_min=row.get("planned_duration_estimate_min"),
        )
        if budget_suffix:
            print(f"       >> {budget_suffix}")
    print()


def _load_control_plane_state(run_id: str | None = None) -> tuple[str | None, list[dict[str, Any]]]:
    service = ControllerService(load_store_from_env())
    selected_run_id = run_id or service.latest_run_id()
    if not selected_run_id:
        return None, []
    view = service.status(selected_run_id)
    rows: list[dict[str, Any]] = []
    for stage in view.stages:
        rows.append(
            {
                "stage": stage.stage_name,
                "status": stage.status,
                "updated_at": stage.heartbeat_at or stage.completed_at or "",
                "blocker_kind": stage.blocker_kind,
                "blocker_detail": stage.blocker_detail,
                "current_attempt_id": stage.current_attempt_id,
                "selected_attempt_id": stage.selected_attempt_id,
                "progress": stage.progress,
                "last_error": stage.last_error,
            }
        )
    return view.run_id, rows


def _show_control_plane_state(run_id: str | None, stage_rows: list[dict[str, Any]]) -> None:
    """Display Postgres-backed control-plane state."""
    if not stage_rows:
        return

    print("=" * 62)
    print("  CONTROL PLANE STATE")
    print("=" * 62)
    print()
    if run_id:
        print(f"  RunManifest: {run_id}")
        print()

    order = {"running": 0, "failed": 1, "dataset_blocked": 2, "manual": 3, "completed": 4}
    stage_rows.sort(
        key=lambda row: (
            order.get(str(row.get("status", "")).lower(), 9),
            row.get("stage", ""),
        )
    )

    for row in stage_rows:
        stage = row.get("stage", "?")
        status = str(row.get("status", "?")).lower()
        updated = row.get("updated_at", "")
        progress_suffix = _format_progress_suffix(row.get("progress"))

        icons = {
            "running": ">>>",
            "completed": "[x]",
            "failed": "[!]",
            "dataset_blocked": "[!]",
            "manual": "[-]",
        }
        icon = icons.get(status, "[?]")

        ts = ""
        if updated and "T" in updated:
            ts = updated.split("T")[1][:5]

        suffix_parts: list[str] = []
        blocker_kind = str(row.get("blocker_kind", "") or "")
        blocker_detail = str(row.get("blocker_detail", "") or "")
        current_attempt_id = str(row.get("current_attempt_id", "") or "")
        selected_attempt_id = str(row.get("selected_attempt_id", "") or "")
        if blocker_kind:
            suffix_parts.append(f"{blocker_kind}:{blocker_detail[:60]}")
        elif current_attempt_id:
            suffix_parts.append(current_attempt_id)
        elif selected_attempt_id:
            suffix_parts.append(f"selected={selected_attempt_id}")
        if progress_suffix:
            suffix_parts.append(progress_suffix)
        policy_suffix = f"  {'/'.join(suffix_parts)}" if suffix_parts else ""

        print(f"  {icon} {stage:35s} {status:15s} {ts:>5s}{policy_suffix}")
        budget_suffix = _runtime_budget_suffix(
            str(stage),
            progress_payload=row.get("progress"),
            updated_at=str(updated or ""),
        )
        if budget_suffix:
            print(f"       >> {budget_suffix}")

    print()


# ── Runtime estimates ─────────────────────────────────────────────────────


def show_estimates() -> None:
    """Show runtime estimates derived from STAGES.duration_estimate_min."""
    print("=" * 62)
    print("  RUNTIME ESTIMATES (30x WGS)")
    print("=" * 62)
    print()

    estimates = []
    for name, stage in sorted(STAGES.items()):
        if stage.duration_estimate_min > 0:
            display = _STAGE_DISPLAY_NAMES.get(name, name.replace("_", " ").title())
            minutes = stage.duration_estimate_min
            if minutes < 5:
                cat = "A: Quick (<5 min)"
            elif minutes < 30:
                cat = "B: Short (5-30 min)"
            elif minutes < 120:
                cat = "C: Medium (30-120 min)"
            else:
                cat = "D: Long (>2 hr)"
            estimates.append((cat, display, minutes))

    by_cat: dict[str, list[tuple[str, int]]] = {}
    for cat, display, minutes in estimates:
        by_cat.setdefault(cat, []).append((display, minutes))

    for cat in sorted(by_cat):
        print(f"  {cat}:")
        for display, minutes in sorted(by_cat[cat], key=lambda item: item[1]):
            if minutes >= 60:
                est = f"~{minutes // 60}h{minutes % 60:02d}m"
            else:
                est = f"~{minutes}m"
            print(f"    {display:30s} {est}")
        print()

    total_stages = len(STAGES)
    est_stages = sum(1 for stage in STAGES.values() if stage.duration_estimate_min > 0)
    print(f"  {est_stages}/{total_stages} stages have estimates")
    print()


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="WGS pipeline status dashboard")
    parser.add_argument("--volume", action="store_true", help="Modal volume only")
    parser.add_argument("--local", action="store_true", help="Local files only")
    parser.add_argument("--apps", action="store_true", help="Running Modal apps only")
    parser.add_argument("--estimate", action="store_true", help="Show runtime estimates")
    parser.add_argument("--run-id", default=None, help="Control-plane run id to inspect")
    args = parser.parse_args()

    show_all = not (args.volume or args.local or args.apps or args.estimate)

    print()
    print(f"  Sample: {SAMPLE_ID}  |  Volume: {VOLUME_NAME}")
    print()

    if args.estimate:
        show_estimates()
        return 0

    if show_all or args.local:
        show_local()

    if show_all or args.volume:
        print("  (probing Modal volume...)")
        probe_data = _run_volume_probe()
        show_volume(probe_data)
        run_id: str | None = None
        stage_rows: list[dict[str, Any]] = []
        # `--volume` is documented as a Modal-volume-only surface.
        should_show_control_plane = show_all or bool(args.run_id)
        if should_show_control_plane:
            try:
                run_id, stage_rows = _load_control_plane_state(args.run_id)
            except RuntimeError as exc:
                print(f"ERROR: {exc}")
                return 2
            if not run_id:
                print("  (no control-plane runs found for the current sample)")
                print()
            else:
                _show_control_plane_state(run_id, stage_rows)
        if show_all or bool(args.run_id):
            _show_reconciliation(
                stage_rows,
                probe_data.get("_worker_receipts", []),
                probe_data.get("_runtime_progress", []),
                probe_data.get("_pipeline_logs", {}),
            )
        _show_active_runtime(
            probe_data.get("_runtime_progress", []),
            probe_data.get("_worker_receipts", []),
            probe_data.get("_pipeline_logs", {}),
        )
        _show_runtime_progress(
            probe_data.get("_runtime_progress", []),
            probe_data.get("_worker_receipts", []),
        )
        _show_worker_receipts(probe_data.get("_worker_receipts", []))
        _show_pipeline_logs(probe_data.get("_pipeline_logs", {}))

    if show_all or args.apps:
        show_apps()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

## File: tests/test_runtime_state.py
```
from __future__ import annotations

import json
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import modal
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import genomics_status
import modal_utils
from freshness import MarkerStore
from genomics_status import _probe_volume_impl, _probe_volume_sdk_impl, _show_pipeline_logs, _show_runtime_progress
from modal_utils import finalize_stage, init_stage
from pipeline_core import load_stage_run, load_stage_run_strict, write_stage_run
from wgs_config import (
    SAMPLE_ID,
    Paths,
    autosome_chromosomes,
    autosome_plus_x_chromosomes,
    autosome_region_csv,
    canonical_status_root,
    load_sample_context,
    status_root_candidates,
)


def test_write_stage_run_round_trip(tmp_path: Path) -> None:
    status_path = tmp_path / "vep" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    write_stage_run(
        status_path,
        "vep",
        "RUNNING",
        sample_id=SAMPLE_ID,
        run_id="run-1",
        attempt_id="attempt-1",
        progress={"stage": "vep", "state": "running", "current": 5, "total": 10},
    )
    running = load_stage_run(status_path)

    assert running is not None
    assert running.status == "RUNNING"
    assert running.duration_sec is None
    assert running.sample_id == SAMPLE_ID
    assert running.run_id == "run-1"
    assert running.attempt_id == "attempt-1"
    assert running.progress["current"] == 5

    write_stage_run(
        status_path,
        "vep",
        "SUCCESS",
        12.34,
        sample_id=SAMPLE_ID,
        signature_hash="abc123",
    )
    success = load_stage_run(status_path)

    assert success is not None
    assert success.status == "SUCCESS"
    assert success.duration_sec == 12.34
    assert success.signature_hash == "abc123"
    assert success.skip_kind == ""
    assert success.skip_reason == ""
    attempt_receipt = status_path.parent / "attempts" / "attempt-1" / "receipt.json"
    mirrored = load_stage_run(attempt_receipt)
    assert mirrored is not None
    assert mirrored.attempt_id == "attempt-1"
    assert mirrored.status == "RUNNING"


def test_write_stage_run_clears_terminal_fields_when_stage_restarts(tmp_path: Path) -> None:
    status_path = tmp_path / "sven_sv" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    write_stage_run(
        status_path,
        "sven_sv",
        "FAILED",
        elapsed=600.0,
        error="old failure",
        completed_at="2026-04-10T22:00:00Z",
        manifest_hash="manifest-old",
        output_manifest=[{"path": "/tmp/out.tsv", "sha256": "abc", "bytes": 123}],
        sample_id=SAMPLE_ID,
        preserve_existing=True,
    )
    write_stage_run(
        status_path,
        "sven_sv",
        "RUNNING",
        sample_id=SAMPLE_ID,
        progress={"stage": "sven_sv", "state": "running", "step": "annotate"},
        preserve_existing=True,
    )

    restarted = load_stage_run(status_path)
    assert restarted is not None
    assert restarted.status == "RUNNING"
    assert restarted.duration_sec is None
    assert restarted.error is None
    assert restarted.completed_at is None
    assert restarted.manifest_hash == ""
    assert restarted.output_manifest == []


def test_probe_volume_reads_stage_local_status_files(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    results_dir = data_dir / "results"
    write_stage_run(
        results_dir / "vep" / "_STATUS.json",
        "vep",
        "SUCCESS",
        9.5,
        sample_id=SAMPLE_ID,
        run_id="probe-1",
        attempt_id="vep-attempt-1",
        progress={
            "stage": "vep",
            "state": "success",
            "current": 10,
            "total": 10,
            "updated_at": "2026-04-10T22:58:00Z",
        },
    )
    write_stage_run(
        results_dir / "other_sample_stage" / "_STATUS.json",
        "other_sample_stage",
        "SUCCESS",
        2.0,
        sample_id="someone-else",
        attempt_id="other-attempt-1",
    )

    probe = _probe_volume_impl([], str(data_dir), SAMPLE_ID)
    states = probe["_worker_receipts"]

    assert [row["stage"] for row in states] == ["vep"]
    assert states[0]["status"] == "SUCCESS"
    assert states[0]["elapsed_s"] == 9.5
    assert states[0]["progress"]["current"] == 10
    assert states[0]["updated_at"] == "2026-04-10T22:58:00Z"


def test_probe_volume_reads_run_scoped_current_progress(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    results_dir = data_dir / "results"
    current_dir = data_dir / "logs" / "current" / "vep"
    write_stage_run(
        results_dir / "vep" / "_STATUS.json",
        "vep",
        "RUNNING",
        sample_id=SAMPLE_ID,
        run_id="probe-1",
        attempt_id="vep-attempt-1",
        progress={"stage": "vep", "state": "running", "current": 3, "total": 10},
    )
    current_dir.mkdir(parents=True, exist_ok=True)
    (current_dir / "probe-1.json").write_text(
        json.dumps(
            {
                "script": "vep",
                "stage": "vep",
                "run_id": "probe-1",
                "state": "running",
                "current": 3,
                "total": 10,
            }
        ),
        encoding="utf-8",
    )
    (current_dir / "latest.json").write_text(
        json.dumps({"script": "vep", "run_id": "probe-1", "state": "running"}),
        encoding="utf-8",
    )
    (data_dir / "logs" / "vep.jsonl").write_text("", encoding="utf-8")

    probe = _probe_volume_impl([], str(data_dir), SAMPLE_ID)

    current = probe["_pipeline_logs"]["scripts"]["vep"]["current"]
    assert current["run_id"] == "probe-1"
    assert current["current"] == 3


def test_probe_volume_reads_runtime_progress_files(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    progress_path = data_dir / "results" / "pangenie" / "pangenie_progress.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps(
            {
                "stage": "pangenie",
                "step": "pangenie_index",
                "message": "running PanGenie-index",
                "elapsed_s": 120.5,
                "index_file_count": 17,
            }
        ),
        encoding="utf-8",
    )
    done_path = data_dir / "results" / "triage" / "triage.progress.json"
    done_path.parent.mkdir(parents=True, exist_ok=True)
    done_path.write_text(json.dumps({"status": "success"}), encoding="utf-8")

    probe = _probe_volume_impl([], str(data_dir), SAMPLE_ID)

    runtime_progress = probe["_runtime_progress"]
    assert len(runtime_progress) == 1
    assert runtime_progress[0]["path"].endswith("pangenie/pangenie_progress.json")
    assert runtime_progress[0]["payload"]["message"] == "running PanGenie-index"


def test_show_runtime_progress_displays_nested_detail_tails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _show_runtime_progress(
        [
            {
                "path": "samples/markus/results/hla_optitype/hla_optitype_progress.json",
                "payload": {
                    "stage": "hla_optitype",
                    "step": "optitype",
                    "message": "running OptiType",
                    "details": {
                        "checkpoint_label": "OptiType MHC FASTQs",
                        "cmd": "OptiTypePipeline.py -i r1 r2 --dna",
                        "stdout_tail": "solving ILP",
                    },
                },
            }
        ]
    )

    output = capsys.readouterr().out
    assert "checkpoint_label: OptiType MHC FASTQs" in output
    assert "cmd: OptiTypePipeline.py -i r1 r2 --dna" in output
    assert "stdout_tail: solving ILP" in output


def test_show_active_runtime_prefers_richer_progress_over_blank_receipt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    genomics_status._show_active_runtime(
        [
            {
                "path": "samples/markus/results/pangenie/pangenie_progress.json",
                "payload": {
                    "stage": "pangenie",
                    "step": "pangenie_genotype",
                    "message": "running PanGenie genotyping",
                    "elapsed_s": 240.0,
                    "updated_at": "2026-04-10T22:10:00Z",
                    "lines": 30,
                },
            }
        ],
        [
            {
                "stage": "pangenie",
                "status": "RUNNING",
                "updated_at": "2026-04-10T22:11:00Z",
                "progress": {
                    "stage": "pangenie",
                    "step": "",
                    "message": "",
                    "updated_at": "2026-04-10T22:11:00Z",
                    "details": {"elapsed_s": 300.0},
                },
            }
        ],
        {"scripts": {}},
    )

    output = capsys.readouterr().out
    assert "ACTIVE RUNTIME" in output
    assert "pangenie" in output
    assert "[progress]" in output
    assert "running PanGenie genotyping" in output


def test_show_active_runtime_ignores_failed_log_snapshots(
    capsys: pytest.CaptureFixture[str],
) -> None:
    genomics_status._show_active_runtime(
        [],
        [
            {
                "stage": "pangenie",
                "status": "RUNNING",
                "updated_at": "2026-04-10T22:11:00Z",
                "progress": {
                    "stage": "pangenie",
                    "step": "pangenie_genotype",
                    "message": "running PanGenie genotyping",
                    "updated_at": "2026-04-10T22:11:00Z",
                },
            }
        ],
        {
            "scripts": {
                "pangenie": {
                    "current": {
                        "script": "pangenie",
                        "stage": "pangenie",
                        "state": "failed",
                        "updated_at": "2026-04-10T22:12:00Z",
                        "message": "PanGenie failed",
                    }
                }
            }
        },
    )

    output = capsys.readouterr().out
    assert "[receipt]" in output
    assert "PanGenie failed" not in output


def test_show_active_runtime_suppresses_stale_progress_after_terminal_receipt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    genomics_status._show_active_runtime(
        [
            {
                "path": "samples/markus/results/pangenie/pangenie_progress.json",
                "payload": {
                    "stage": "pangenie",
                    "step": "pangenie_genotype",
                    "message": "running PanGenie genotyping",
                    "updated_at": "2026-04-10T22:10:00Z",
                },
            }
        ],
        [
            {
                "stage": "pangenie",
                "status": "FAILED",
                "updated_at": "2026-04-10T22:12:00Z",
                "progress": {
                    "stage": "pangenie",
                    "state": "failed",
                    "message": "PanGenie failed",
                    "updated_at": "2026-04-10T22:12:00Z",
                },
            }
        ],
        {"scripts": {}},
    )

    output = capsys.readouterr().out
    assert "ACTIVE RUNTIME" not in output


def test_run_cmd_emits_live_output_tails_and_auto_checkpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    commits: list[str] = []

    class _FakeVolume:
        def commit(self) -> None:
            commits.append("commit")

    class _FakeLogger:
        def __init__(self) -> None:
            self.heartbeats: list[tuple[str, dict[str, object]]] = []
            self.infos: list[tuple[str, dict[str, object]]] = []

        def info(self, msg: str, **kw: object) -> None:
            self.infos.append((msg, kw))

        def heartbeat(self, stage: str, **kw: object) -> None:
            self.heartbeats.append((stage, kw))

    logger = _FakeLogger()
    monkeypatch.setattr(modal_utils, "vol", _FakeVolume())
    code = textwrap.dedent(
        """
        import sys, time
        print("stdout-start", flush=True)
        sys.stderr.write("stderr-start\\n")
        sys.stderr.flush()
        time.sleep(0.15)
        print("stdout-mid", flush=True)
        sys.stderr.write("stderr-mid\\n")
        sys.stderr.flush()
        time.sleep(0.15)
        print("stdout-end", flush=True)
        """
    )

    stdout = modal_utils.run_cmd(
        ["python3", "-u", "-c", code],
        timeout_s=5,
        logger=logger,
        progress_stage="test_stage",
        progress_step="long_step",
        heartbeat_s=0.05,
    )

    assert "stdout-end" in stdout
    assert commits == ["commit"]
    assert logger.heartbeats
    assert any("stderr-start" in (payload.get("stderr_tail", "") or "") for _, payload in logger.heartbeats)
    assert any("stdout-start" in (payload.get("stdout_tail", "") or "") for _, payload in logger.heartbeats)


@dataclass
class _FakeEntryType:
    name: str
    value: int


@dataclass
class _FakeVolumeEntry:
    path: str
    type: _FakeEntryType
    size: int = 0
    mtime: int = 0


class _FakeProbeVolume:
    def __init__(self, tree: dict[str, list[_FakeVolumeEntry]], files: dict[str, str]) -> None:
        self.tree = tree
        self.files = files

    def listdir(self, path: str, *, recursive: bool = False) -> list[_FakeVolumeEntry]:
        normalized = path.rstrip("/")
        if recursive:
            prefix = f"{normalized}/" if normalized else ""
            results: list[_FakeVolumeEntry] = []
            for key, entries in self.tree.items():
                if key == normalized or key.startswith(prefix):
                    results.extend(entries)
            if results:
                return results
        if normalized not in self.tree:
            raise modal.exception.NotFoundError("No such file or directory")
        return self.tree[normalized]

    def read_file(self, path: str):
        normalized = path.rstrip("/")
        if normalized not in self.files:
            raise modal.exception.NotFoundError("No such file or directory")
        return [self.files[normalized].encode("utf-8")]


def test_probe_volume_sdk_reads_receipts_progress_and_current_logs() -> None:
    directory = _FakeEntryType("DIRECTORY", 2)
    file_type = _FakeEntryType("FILE", 1)
    fake_volume = _FakeProbeVolume(
        tree={
            "samples/markus/results": [
                _FakeVolumeEntry("samples/markus/results/pangenie", directory, mtime=10),
            ],
            "samples/markus/results/pangenie": [
                _FakeVolumeEntry("samples/markus/results/pangenie/attempts", directory, mtime=10),
                _FakeVolumeEntry(
                    "samples/markus/results/pangenie/pangenie_progress.json",
                    file_type,
                    size=128,
                    mtime=11,
                ),
            ],
            "samples/markus/results/pangenie/attempts": [
                _FakeVolumeEntry(
                    "samples/markus/results/pangenie/attempts/pangenie-attempt-1",
                    directory,
                    mtime=12,
                ),
            ],
            "logs/current": [
                _FakeVolumeEntry("logs/current/pangenie", directory, mtime=13),
            ],
            "logs": [
                _FakeVolumeEntry("logs/pangenie.jsonl", file_type, size=256, mtime=13),
            ],
            "logs/current/pangenie": [
                _FakeVolumeEntry("logs/current/pangenie/latest.json", file_type, size=64, mtime=13),
                _FakeVolumeEntry("logs/current/pangenie/run-1.json", file_type, size=128, mtime=13),
            ],
        },
        files={
            "samples/markus/results/pangenie/attempts/pangenie-attempt-1/receipt.json": json.dumps(
                {
                    "stage": "pangenie",
                    "status": "RUNNING",
                    "timestamp": "2026-04-10T22:03:41Z",
                    "sample_id": SAMPLE_ID,
                    "sample_source": "saliva",
                    "planned_resource_class": "ResourceClass.CPU",
                    "applicability_policy": "allowed",
                    "applicability_trust_class": "trusted",
                    "applicability_reason": "",
                    "run_id": "pangenie-run-1",
                    "progress": {
                        "message": "running PanGenie-index",
                        "updated_at": "2026-04-10T22:05:41Z",
                    },
                    }
                ),
            "samples/markus/results/pangenie/pangenie_progress.json": json.dumps(
                {
                    "stage": "pangenie",
                    "message": "running PanGenie-index",
                    "elapsed_s": 120.5,
                }
            ),
            "logs/current/pangenie/latest.json": json.dumps(
                {
                    "script": "pangenie",
                    "run_id": "run-1",
                    "state": "running",
                }
            ),
            "logs/current/pangenie/run-1.json": json.dumps(
                {
                    "script": "pangenie",
                    "stage": "pangenie",
                    "run_id": "run-1",
                    "state": "running",
                    "message": "running PanGenie-index",
                }
            ),
            "logs/pangenie.jsonl": "\n".join(
                [
                    json.dumps(
                        {
                            "ts": "2026-04-10T22:05:00Z",
                            "level": "START",
                            "stage": "pangenie",
                            "msg": "started",
                        }
                    ),
                    json.dumps(
                        {
                            "ts": "2026-04-10T22:06:00Z",
                            "level": "HEARTBEAT",
                            "stage": "pangenie",
                            "msg": "running PanGenie-index",
                        }
                    ),
                ]
            ),
        },
    )

    probe = _probe_volume_sdk_impl(fake_volume, [], SAMPLE_ID)

    assert probe["_worker_receipts"][0]["stage"] == "pangenie"
    assert probe["_worker_receipts"][0]["progress"]["message"] == "running PanGenie-index"
    assert probe["_worker_receipts"][0]["updated_at"] == "2026-04-10T22:05:41Z"
    assert probe["_runtime_progress"][0]["path"] == "samples/markus/results/pangenie/pangenie_progress.json"
    assert probe["_pipeline_logs"]["scripts"]["pangenie"]["current"]["run_id"] == "run-1"
    assert probe["_pipeline_logs"]["scripts"]["pangenie"]["total_entries"] == 2
    assert probe["_pipeline_logs"]["scripts"]["pangenie"]["recent"][-1]["level"] == "HEARTBEAT"


def test_show_pipeline_logs_falls_back_to_current_snapshot_when_log_tail_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _show_pipeline_logs(
        {
            "exists": True,
            "scripts": {
                "sven_sv": {
                    "total_entries": 0,
                    "recent": [],
                    "size": 0,
                    "current": {
                        "script": "sven_sv",
                        "stage": "sven_sv",
                        "step": "sven_annotate",
                        "state": "running",
                        "message": "get_annotations.py populating annotations",
                        "updated_at": "2026-04-11T01:30:00Z",
                    },
                }
            },
        }
    )

    output = capsys.readouterr().out
    assert "HEARTBEAT sven_annotate" in output
    assert "(01:30 UTC)" in output


def test_main_volume_mode_skips_control_plane_without_run_id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--volume` should not require a Postgres DSN when no run is requested."""
    monkeypatch.setattr(
        genomics_status,
        "_run_volume_probe",
        lambda: {"_runtime_progress": [], "_worker_receipts": [], "_pipeline_logs": {}},
    )
    monkeypatch.setattr(genomics_status, "show_volume", lambda probe_data: None)
    monkeypatch.setattr(
        genomics_status,
        "_load_control_plane_state",
        lambda run_id: (_ for _ in ()).throw(AssertionError("control plane should not load")),
    )
    monkeypatch.setattr(sys, "argv", ["genomics_status.py", "--volume"])

    assert genomics_status.main() == 0
    assert "ERROR:" not in capsys.readouterr().out


def test_runtime_budget_suffix_formats_elapsed_estimate_timeout_and_age() -> None:
    suffix = genomics_status._runtime_budget_suffix(
        "sven_sv",
        progress_payload={"elapsed_s": 3600, "max_silence_s": 900},
        updated_at="2026-04-10T22:55:00Z",
        planned_duration_estimate_min=120,
        now=genomics_status._parse_timestamp("2026-04-10T23:00:00Z"),
    )

    assert "elapsed 1h00m" in suffix
    assert "est 2h00m" in suffix
    assert "timeout in 5h00m" in suffix
    assert "age 5m" in suffix


def test_runtime_budget_suffix_flags_stale_and_over_estimate() -> None:
    suffix = genomics_status._runtime_budget_suffix(
        "pangenie",
        progress_payload={"details": {"elapsed_s": 9100}, "max_silence_s": 900},
        updated_at="2026-04-10T22:30:00Z",
        planned_duration_estimate_min=120,
        now=genomics_status._parse_timestamp("2026-04-10T22:50:30Z"),
    )

    assert "elapsed 2h31m" in suffix
    assert "over est" in suffix
    assert "stale>15m" in suffix


def test_reconcile_stage_rows_flags_bridge_failed_when_receipt_is_terminal() -> None:
    rows = genomics_status._reconcile_stage_rows(
        [],
        [
            {
                "stage": "vep",
                "status": "SUCCESS",
                "updated_at": "2026-04-10T22:58:00Z",
                "progress": {},
            }
        ],
        [],
        {"scripts": {}},
        local_bridge_state={"vep": {"available": False, "detail": "local dir missing"}},
    )

    assert rows == [
        {
            "stage": "vep",
            "class": "bridge_failed",
            "evidence": "receipt=success local=missing",
            "detail": "worker reached a terminal receipt, but local output is missing",
            "local_detail": "local dir missing",
        }
    ]


def test_reconcile_stage_rows_flags_incomplete_attempt_without_runtime_signal() -> None:
    rows = genomics_status._reconcile_stage_rows(
        [{"stage": "triage", "status": "running", "updated_at": "2026-04-10T23:00:00Z"}],
        [],
        [],
        {"scripts": {}},
        local_bridge_state={"triage": {"available": False, "detail": "local dir missing"}},
    )

    assert rows == [
        {
            "stage": "triage",
            "class": "incomplete_attempt",
            "evidence": "cp=running local=missing",
            "detail": "control plane expects active work, but no current runtime signal was found",
            "local_detail": "local dir missing",
        }
    ]


def test_reconcile_stage_rows_flags_local_stale_when_runtime_is_active() -> None:
    rows = genomics_status._reconcile_stage_rows(
        [{"stage": "pangenie", "status": "running", "updated_at": "2026-04-10T23:00:00Z"}],
        [
            {
                "stage": "pangenie",
                "status": "RUNNING",
                "updated_at": "2026-04-10T23:01:00Z",
                "progress": {"stage": "pangenie", "message": "running PanGenie-index"},
            }
        ],
        [
            {
                "path": "samples/markus/results/pangenie/pangenie_progress.json",
                "payload": {
                    "stage": "pangenie",
                    "message": "running PanGenie-index",
                    "updated_at": "2026-04-10T23:02:00Z",
                },
            }
        ],
        {"scripts": {}},
        local_bridge_state={"pangenie": {"available": True, "detail": "3 local file(s)"}},
    )

    assert rows == [
        {
            "stage": "pangenie",
            "class": "local_stale",
            "evidence": "cp=running receipt=running runtime=progress local=ready",
            "detail": "local bridge exists but a newer run is still active",
            "local_detail": "3 local file(s)",
        }
    ]


def test_marker_store_scans_latest_receipts(tmp_path: Path) -> None:
    write_stage_run(
        tmp_path / "triage" / "_STATUS.json",
        "triage",
        "SUCCESS",
        4.2,
        sample_id=SAMPLE_ID,
        signature_hash="sig-1",
        attempt_id="triage-attempt-1",
    )

    store = MarkerStore(status_dir=tmp_path)
    markers = store.all_markers()

    assert "triage" in markers
    assert markers["triage"].qc_passed is True


def test_marker_store_prefers_attempt_receipt_over_stage_mirror(tmp_path: Path) -> None:
    write_stage_run(
        tmp_path / "triage" / "_STATUS.json",
        "triage",
        "RUNNING",
        sample_id=SAMPLE_ID,
        attempt_id="triage-attempt-1",
    )
    write_stage_run(
        tmp_path / "triage" / "attempts" / "triage-attempt-2" / "receipt.json",
        "triage",
        "SUCCESS",
        8.5,
        sample_id=SAMPLE_ID,
        attempt_id="triage-attempt-2",
        signature_hash="sig-2",
    )

    marker = MarkerStore(status_dir=tmp_path).get("triage")

    assert marker is not None
    assert marker.signature == "sig-2"
    assert marker.qc_passed is True


def test_write_stage_run_preserve_existing_metadata(tmp_path: Path) -> None:
    status_path = tmp_path / "triage" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    write_stage_run(
        status_path,
        "triage",
        "SUCCESS",
        4.2,
        sample_id=SAMPLE_ID,
        signature_hash="sig-1",
        db_versions={"clinvar": "2026-03-31"},
        config_hashes={"triage": "cfg-1"},
    )
    write_stage_run(
        status_path,
        "triage",
        "FAILED",
        5.0,
        sample_id=SAMPLE_ID,
        preserve_existing=True,
    )

    status = load_stage_run(status_path)

    assert status is not None
    assert status.status == "FAILED"
    assert status.signature_hash == "sig-1"
    assert status.db_versions == {"clinvar": "2026-03-31"}
    assert status.config_hashes == {"triage": "cfg-1"}


def test_load_stage_run_strict_fails_on_malformed_status_json(tmp_path: Path) -> None:
    status_path = tmp_path / "triage" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text("{not-json}", encoding="utf-8")

    assert load_stage_run(status_path) is None

    with pytest.raises(Exception):
        load_stage_run_strict(status_path)


def test_load_stage_run_strict_rejects_unknown_fields(tmp_path: Path) -> None:
    status_path = tmp_path / "triage" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "stage": "triage",
                "status": "SUCCESS",
                "unexpected_extra": "nope",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        load_stage_run_strict(status_path)


def test_write_stage_run_rejects_malformed_progress_payload(tmp_path: Path) -> None:
    status_path = tmp_path / "triage" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(Exception, match="ProgressSnapshot|progress"):
        write_stage_run(
            status_path,
            "triage",
            "RUNNING",
            sample_id=SAMPLE_ID,
            progress=["not", "a", "snapshot"],  # type: ignore[arg-type]
        )


def test_load_stage_run_strict_rejects_malformed_progress_payload(tmp_path: Path) -> None:
    status_path = tmp_path / "triage" / "_STATUS.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "stage": "triage",
                "status": "RUNNING",
                "progress": ["not", "a", "snapshot"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="ProgressSnapshot|progress"):
        load_stage_run_strict(status_path)


def test_status_roots_are_results_only(tmp_path: Path) -> None:
    assert status_root_candidates(data_dir=tmp_path) == (tmp_path / "results",)
    assert canonical_status_root(data_dir=tmp_path) == tmp_path / "results"


def test_paths_expose_analysis_and_runtime_stage_helpers(tmp_path: Path) -> None:
    paths = Paths(sample_id="tester", data_dir=tmp_path)

    assert (
        paths.analysis_stage_dir("haplotype_biography")
        == tmp_path / "analysis" / "haplotype_biography"
    )
    assert paths.analysis_artifact("roh_gnomad", "roh_regions.tsv") == (
        tmp_path / "analysis" / "roh_gnomad" / "roh_regions.tsv"
    )
    assert paths.runtime_stage_dir("roh_gnomad") == tmp_path / "results" / "roh_gnomad"
    assert paths.runtime_stage_artifact("roh_gnomad", "roh_gnomad_summary.json") == (
        tmp_path / "results" / "roh_gnomad" / "roh_gnomad_summary.json"
    )


def test_load_sample_context_falls_back_to_cwd_mounted_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config" / "samples" / "donor.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
{
  "sample_id": "donor",
  "assembly": "hg38",
  "sequencing": {
    "provider": "Nebula",
    "type": "WGS",
    "coverage": "30x",
    "source": "saliva",
    "variant_caller": "DeepVariant"
  }
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    context = load_sample_context("donor", repo_root=tmp_path / "missing")

    assert context.sample_id == "donor"
    assert context.normalized_source == "saliva"
    assert context.metadata_path.endswith("config/samples/donor.json")


def test_chromosome_helpers_keep_autosome_and_narrative_sets_distinct() -> None:
    assert autosome_chromosomes()[:3] == ["chr1", "chr2", "chr3"]
    assert autosome_chromosomes()[-1] == "chr22"
    assert autosome_plus_x_chromosomes()[-1] == "chrX"
    assert autosome_region_csv() == ",".join(autosome_chromosomes())


def test_stage_decorator_rejects_mismatched_init_stage_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "rare_variant_triage"
    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    from pipeline_core import stage

    @stage("rare_variant_triage", str(out_dir))
    def run_stage() -> None:
        init_stage(str(out_dir), "triage")

    try:
        with pytest.raises(AssertionError, match="stage mismatch"):
            run_stage()
    finally:
        modal_utils._current_stage = None
        modal_utils._stage_start_time = None

    status = load_stage_run(out_dir / "_STATUS.json")
    assert status is not None
    assert status.status == "FAILED"


def test_stage_decorator_rejects_mismatched_finalize_stage_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "rare_variant_triage"
    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    from pipeline_core import stage

    @stage("rare_variant_triage", str(out_dir))
    def run_stage() -> None:
        init_stage(str(out_dir), "rare_variant_triage")
        finalize_stage(
            {"total_variants": 1},
            out_dir / "triage_summary.json",
            stage_name="triage",
        )

    try:
        with pytest.raises(AssertionError, match="stage mismatch"):
            run_stage()
    finally:
        modal_utils._current_stage = None
        modal_utils._stage_start_time = None

    status = load_stage_run(out_dir / "_STATUS.json")
    assert status is not None
    assert status.status == "FAILED"


def test_stage_decorator_records_applicability_and_planned_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "chip_screening"
    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    from pipeline_core import stage

    @stage("chip_screening", str(out_dir))
    def run_stage() -> None:
        init_stage(str(out_dir), "chip_screening")

    try:
        run_stage()
    finally:
        modal_utils._current_stage = None
        modal_utils._stage_start_time = None

    status = load_stage_run(out_dir / "_STATUS.json")
    assert status is not None
    assert status.status == "SUCCESS"
    assert status.applicability_policy == "caution"
    assert status.applicability_trust_class == "exploratory"
    assert status.assay_support == "limited"
    assert status.default_lifecycle_state == "research_only"
    assert status.sample_modality_mismatch is True
    assert status.requires_new_assay is False
    assert status.sample_source == "saliva"
    assert status.planned_resource_class == "cpu"
    assert status.actual_resource_class == "cpu"


def test_stage_decorator_records_pipeline_attempt_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "chip_screening"
    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)
    monkeypatch.setenv("PIPELINE_ATTEMPT_ID", "attempt-stage-123")

    from pipeline_core import stage

    @stage("chip_screening", str(out_dir))
    def run_stage() -> None:
        init_stage(str(out_dir), "chip_screening")

    try:
        run_stage()
    finally:
        modal_utils._current_stage = None
        modal_utils._stage_start_time = None
        monkeypatch.delenv("PIPELINE_ATTEMPT_ID", raising=False)

    status = load_stage_run(out_dir / "_STATUS.json")
    assert status is not None
    assert status.attempt_id == "attempt-stage-123"


def test_init_stage_reports_running_to_worker_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "triage"
    running_calls: list[dict[str, str]] = []

    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    import orchestrator.worker_client as worker_client

    monkeypatch.setattr(
        worker_client,
        "record_running",
        lambda **kwargs: running_calls.append(kwargs),
    )

    init_stage(str(out_dir), "triage")

    assert running_calls == [
        {
            "stage_name": "triage",
            "receipt_path": str(out_dir / "_STATUS.json"),
        }
    ]

    modal_utils._current_stage = None
    modal_utils._stage_start_time = None


def test_init_stage_skips_reload_and_tombstone_inside_matching_stage_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pipeline_core

    out_dir = tmp_path / "triage"
    status_path = out_dir / "_STATUS.json"
    write_stage_run(
        status_path,
        "triage",
        "RUNNING",
        sample_id=SAMPLE_ID,
        run_id="fresh-run",
        attempt_id="fresh-attempt",
        timestamp="2026-04-10T23:45:00Z",
        progress={"stage": "triage", "state": "running", "message": "fresh"},
    )

    calls: list[str] = []
    monkeypatch.setattr(
        modal_utils,
        "vol",
        SimpleNamespace(
            reload=lambda: calls.append("reload"),
            commit=lambda: calls.append("commit"),
        ),
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    import orchestrator.worker_client as worker_client

    monkeypatch.setattr(
        worker_client,
        "record_running",
        lambda **kwargs: calls.append("record_running"),
    )

    token = pipeline_core._ACTIVE_STAGE_CONTEXT.set(("triage", str(out_dir.resolve())))
    try:
        init_stage(str(out_dir), "triage")
    finally:
        pipeline_core._ACTIVE_STAGE_CONTEXT.reset(token)
        modal_utils._current_stage = None
        modal_utils._stage_start_time = None

    status = load_stage_run_strict(status_path)
    assert calls == []
    assert status.run_id == "fresh-run"
    assert status.attempt_id == "fresh-attempt"
    assert status.progress["message"] == "fresh"


def test_finalize_stage_reports_success_to_worker_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "triage"
    output_path = out_dir / "summary.json"
    terminal_calls: list[dict[str, str]] = []

    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    import orchestrator.worker_client as worker_client

    monkeypatch.setattr(
        worker_client,
        "record_terminal_state",
        lambda **kwargs: terminal_calls.append(kwargs),
    )

    init_stage(str(out_dir), "triage")
    finalize_stage({"value": 1}, output_path, stage_name="triage")

    assert terminal_calls == [
        {
            "stage_name": "triage",
            "worker_status": "SUCCESS",
            "receipt_path": str(output_path.parent / "_STATUS.json"),
            "manifest_hash": "",
        }
    ]


def test_init_stage_skips_open_file_reload_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "cpsr"
    commit_calls: list[str] = []

    def reload_conflict() -> None:
        raise RuntimeError(
            "there are open files preventing the operation: path samples/markus/results/cpsr/tmp.vcf is open"
        )

    monkeypatch.setattr(
        modal_utils,
        "vol",
        SimpleNamespace(reload=reload_conflict, commit=lambda: commit_calls.append("commit")),
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    init_stage(str(out_dir), "cpsr")

    captured = capsys.readouterr()
    assert "vol.reload() skipped due to open-file conflict" in captured.out
    assert out_dir.exists()
    assert commit_calls == ["commit"]

    modal_utils._current_stage = None
    modal_utils._stage_start_time = None


def test_init_stage_propagates_non_conflict_reload_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "triage"

    def reload_failure() -> None:
        raise RuntimeError("volume unavailable")

    monkeypatch.setattr(
        modal_utils,
        "vol",
        SimpleNamespace(reload=reload_failure, commit=lambda: None),
    )

    with pytest.raises(RuntimeError, match="volume unavailable"):
        init_stage(str(out_dir), "triage")

    modal_utils._current_stage = None
    modal_utils._stage_start_time = None


def test_stage_decorator_records_skip_kind_for_blocked_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pipeline_core

    out_dir = tmp_path / "chip_screening"
    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pipeline_core,
        "_stage_runtime_metadata",
        lambda _name: {
            "planned_resource_class": "cpu",
            "planned_duration_estimate_min": None,
            "actual_resource_class": "cpu",
            "applicability_policy": "blocked",
            "applicability_trust_class": "exploratory",
            "applicability_reason": "blocked for test",
            "assay_support": "unsupported",
            "default_lifecycle_state": "not_assessable",
            "sample_modality_mismatch": True,
            "requires_new_assay": True,
            "sample_source": "saliva",
            "sample_modality": "wgs",
        },
    )

    from pipeline_core import stage

    @stage("chip_screening", str(out_dir))
    def run_stage() -> None:
        return None

    try:
        run_stage()
    finally:
        modal_utils._current_stage = None
        modal_utils._stage_start_time = None

    status = load_stage_run_strict(out_dir / "_STATUS.json")
    assert status.status == "SKIPPED"
    assert status.skip_kind == "applicability_blocked"
    assert status.skip_reason
    assert status.assay_support == "unsupported"
    assert status.default_lifecycle_state == "not_assessable"


def test_write_stage_run_refreshes_timestamp_when_progress_updates(tmp_path: Path) -> None:
    status_path = tmp_path / "vep" / "_STATUS.json"
    write_stage_run(
        status_path,
        "vep",
        "RUNNING",
        sample_id=SAMPLE_ID,
        run_id="vep-run",
        attempt_id="vep-attempt",
        timestamp="2026-04-09T17:31:21Z",
        progress={"stage": "vep", "state": "running", "message": "old"},
    )

    write_stage_run(
        status_path,
        "vep",
        "RUNNING",
        sample_id=SAMPLE_ID,
        run_id="vep-run",
        attempt_id="vep-attempt",
        progress={"stage": "vep", "state": "running", "message": "fresh"},
        preserve_existing=True,
    )

    status = load_stage_run_strict(status_path)
    assert status.progress["message"] == "fresh"
    assert status.timestamp != "2026-04-09T17:31:21Z"


def test_local_stage_skip_writes_skip_kind_and_unified_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENOMICS_SAMPLE_ID", SAMPLE_ID)
    monkeypatch.setattr(
        modal_utils, "vol", SimpleNamespace(reload=lambda: None, commit=lambda: None)
    )
    monkeypatch.setattr(modal_utils, "log_stage_state", lambda *args, **kwargs: None)

    from pipeline_core import local_stage

    out_dir = tmp_path / "demo"
    output_name = "demo.json"
    (out_dir / output_name).parent.mkdir(parents=True, exist_ok=True)
    (out_dir / output_name).write_text('{"existing": true}\n', encoding="utf-8")

    @local_stage("demo_stage", str(out_dir), expected_outputs=[output_name], idempotent=True)
    def run_stage() -> dict[str, str]:
        return {"unexpected": "rerun"}

    run_stage()

    status = load_stage_run_strict(out_dir / "_STATUS.json")
    assert status.status == "SKIPPED"
    assert status.skip_kind == "output_exists"
    assert status.skip_reason == str(out_dir / output_name)


def test_local_stage_auto_write_uses_stage_run_schema_version(tmp_path: Path) -> None:
    from pipeline_core import STAGE_RUN_SCHEMA_VERSION, local_stage

    out_dir = tmp_path / "demo"

    @local_stage("demo_stage", str(out_dir), expected_outputs=["demo.json"])
    def run_stage() -> dict[str, str]:
        return {"payload": "ok"}

    run_stage()

    payload = (out_dir / "demo.json").read_text(encoding="utf-8")
    assert f'"schema_version": "{STAGE_RUN_SCHEMA_VERSION}"' in payload

```

## File: justfile
```
# Genomics — Pipeline runner for WGS analysis
#
# Usage: just --list

# ── Status & Monitoring ───────────────────────────────────────────

# Full pipeline status dashboard
[group('status')]
status:
    uv run python scripts/genomics_status.py

# Modal volume status only
[group('status')]
status-volume:
    uv run python scripts/genomics_status.py --volume

# Local files status only
[group('status')]
status-local:
    uv run python scripts/genomics_status.py --local

# Running Modal apps only
[group('status')]
status-apps:
    uv run python scripts/genomics_status.py --apps

# ── Setup ─────────────────────────────────────────────────────────

# Create symlinks to SSD storage (data/wgs, databases)
[group('setup')]
setup-volumes:
    bash scripts/setup-volumes.sh

# Install tracked git hook wrappers into .git/hooks for this checkout
[group('setup')]
install-hooks:
    uv run python3 scripts/git_hooks.py install

# Verify .git/hooks matches tracked wrappers
[group('setup')]
check-hooks:
    uv run python3 scripts/git_hooks.py check

# Generate a new script from template (tool|panel|analysis)
[group('setup')]
new-stage kind name:
    uv run python scripts/new_stage.py {{kind}} {{name}}

# Validate environment before pipeline runs
[group('setup')]
preflight:
    uv run python scripts/preflight.py

# Preflight check, exit 1 on warnings
[group('setup')]
preflight-strict:
    uv run python scripts/preflight.py --strict

# Bootstrap worktree with sibling path dependencies (biomedical-mcp)
[group('setup')]
bootstrap-worktree:
    bash scripts/bootstrap_worktree.sh

# Validate orchestrator changes offline before restarting a live run
[group('quality')]
validate-orchestrator:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "[validate-orchestrator]"
    echo "  1/4 Syntax check..."
    python3 -m py_compile scripts/pipeline_orchestrator.py
    echo "  ✓ syntax OK"
    echo "  2/4 Import check..."
    PYTHONPATH=scripts uv run python3 -c "import pipeline_orchestrator; print('  ✓ imports OK')"
    echo "  3/4 Unit tests..."
    PYTHONPATH=scripts uv run python3 -m pytest -q tests/test_pipeline_planning.py -x 2>&1 | tail -3
    echo "  4/4 Lint..."
    uv run ruff check scripts/pipeline_orchestrator.py --select F401,F841 -q
    echo "  ✓ validate-orchestrator passed"

# Pipeline Doctor — unified validation (standard, --quick, --full)
[group('quality')]
doctor *ARGS:
    uv run python3 scripts/pipeline_doctor.py {{ARGS}}

# Smoke test — quick sanity checks on pipeline outputs
[group('quality')]
smoke:
    uv run python scripts/pipeline_qc_smoke.py

# End-to-end smoke test — validates pipeline output existence and shape
[group('quality')]
smoke-e2e:
    uv run pytest tests/test_smoke_e2e.py tests/test_properties.py -v --tb=short

# ── Benchmarks & Evals ──────────────────────────────────────────

# PGx concordance: Aldy vs PharmCAT
[group('quality')]
pgx-concordance:
    uv run python scripts/aldy_pharmcat_concordance.py

# PRS sanity check
[group('quality')]
prs-sanity:
    uv run python scripts/prs_sanity_check.py

# Evidence contract validation
[group('quality')]
evidence-preflight:
    uv run python scripts/evidence_preflight.py

# Repo-reality check before dataset or integration work
[group('quality')]
integration-preflight *ARGS:
    uv run python3 scripts/integration_preflight.py {{ARGS}}

# Generate current repo + SSD integration inventory
[group('quality')]
integration-ground-truth:
    uv run python3 scripts/refresh_integration_ground_truth.py

# Flag integration/status docs whose claims no longer match live repo state
[group('quality')]
check-integration-docs:
    uv run python3 scripts/audit_integration_docs.py

# Run the full docs verification stack
[group('quality')]
check-docs: check-claude-md check-integration-docs lint-docs

# Docs hygiene: archive stale plan snapshots, ban tracked backups/logs in active docs
[group('quality')]
lint-docs:
    uv run python3 scripts/lint_docs_hygiene.py

# Lint phenotype consumers to prevent regressions to legacy markdown sources
[group('quality')]
lint-phenotype-contract:
    uv run python3 scripts/lint_phenotype_contract_paths.py

# Validate structured phenotype exports from selve
[group('quality')]
phenotype-contract-validate *ARGS:
    uv run python3 scripts/validate_phenotype_contract.py {{ARGS}}

# Known-variant spot checks
[group('quality')]
spotcheck:
    uv run python scripts/known_variant_spotcheck.py

# Regression snapshot — capture baseline
[group('quality')]
snapshot-baseline:
    uv run python scripts/regression_snapshot.py baseline

# Regression snapshot — check against baseline
[group('quality')]
snapshot-check:
    uv run python scripts/regression_snapshot.py check

# Gold output test — compare review packets against frozen gold
[group('quality')]
gold-check:
    uv run python scripts/gold_output_test.py check

# Freeze current review packets as gold standard
[group('quality')]
gold-freeze:
    uv run python scripts/gold_output_test.py freeze

# Canary gate — sentinel variant classification regression
[group('quality')]
canary:
    uv run python scripts/canary_gate.py

# IR canary — assertion-level invariants (no double-counting, stable policy, no orphans, determinism)
[group('quality')]
ir-canary:
    uv run python scripts/test_ir_canary.py

# Build CaseBundle — the canonical OCDV product contract
[group('quality')]
case-bundle:
    uv run python scripts/case_bundle_builder.py --summary

# Trial balance — disposition ledger + completeness check (log mode)
[group('quality')]
trial-balance:
    uv run python scripts/case_bundle_builder.py --summary 2>&1 | grep -E "Trial balance|Open uncertainties|Audit"

# Lint: product-layer code should consume CaseBundle, not raw stage artifacts
[group('quality')]
lint-product-imports:
    uv run python scripts/lint_product_imports.py --strict

# QC gates — evaluate configurable thresholds
[group('quality')]
qc-gates:
    uv run python scripts/parse_qc_gates.py

# Classification drift check
[group('quality')]
drift-check:
    uv run python scripts/classification_drift.py check

# Classification drift record baseline
[group('quality')]
drift-record:
    uv run python scripts/classification_drift.py record

# Run manifest — capture provenance snapshot
[group('quality')]
run-manifest:
    uv run python scripts/run_manifest.py

# Sample fingerprint — CRAM/VCF identity concordance
[group('quality')]
fingerprint:
    uv run python scripts/sample_fingerprint.py

# Verify provenance of pipeline run (v2 status, manifest hashes)
[group('quality')]
verify-provenance *ARGS:
    uv run python scripts/verify_run_provenance.py {{ARGS}}

# Generate MANIFEST.json — agent-readable index of all stage outputs
[group('pipeline')]
generate-manifest:
    uv run python scripts/generate_manifest.py

# Verify genotype interpretation dicts against allele contracts
[group('quality')]
verify-genotypes:
    uv run python scripts/verify_genotypes.py

# Validate upstream tool output schemas
[group('quality')]
schema-check:
    uv run python scripts/validate_tool_schemas.py

# Run registry-declared QC checks against present local artifacts
[group('quality')]
registry-qc:
    uv run python3 scripts/registry_qc.py

# Import boundary enforcement
[group('quality')]
lint-imports:
    uv run lint-imports

# Architecture debt ratchet (repo hygiene, hooks, runtime ownership)
[group('quality')]
lint-architecture:
    uv run python3 scripts/lint_architecture.py

# Pyright on 10 core shared modules (uses scripts/pyrightconfig.json)
[group('quality')]
type-check-core:
    cd scripts && pyright

# Snapshot schema drift detection (syrupy — auto_classify + config schemas)
[group('quality')]
snapshot-test:
    uv run pytest tests/test_output_snapshots.py -v

# Typing debt ratchet — counts must never increase
[group('quality')]
type-coverage:
    uv run python3 scripts/type_coverage.py

# Fail-loud loader lint — broad except + empty fallback is blocked
[group('quality')]
lint-silent-fallbacks:
    uv run python3 scripts/lint_silent_fallbacks.py

# stage_artifact() template string lint — catches {trait_id} literal bugs
[group('quality')]
lint-template-strings:
    uv run python3 scripts/lint_template_strings.py

# Structural contract tests for repo/runtime and product reports
[group('quality')]
repo-contracts:
    uv run python3 -m pytest tests/test_repo_contracts.py -q

[group('quality')]
report-contracts:
    uv run python3 -m pytest tests/test_report_contracts.py tests/test_render_purity_contracts.py tests/test_surface_projection.py -q

# Mutation testing on auto_classify() — find untested classification branches
[group('quality')]
mutmut-classify:
    uv run mutmut run --paths-to-mutate scripts/generate_review_packets.py --tests-dir tests/ --runner "uv run pytest tests/test_core_logic.py tests/test_invariants.py -x -q" 2>&1 | tail -20

# Count bare subprocess.run calls (should trend toward 0 on critical path)
[group('quality')]
lint-subprocess:
    @echo "Bare subprocess calls (excluding run_cmd wrappers and tests):"
    @grep -rn 'subprocess\.run\|subprocess\.Popen\|subprocess\.call' scripts/*.py | grep -v 'run_cmd\|#.*subprocess\|test_\|def run_cmd\|ToolError' | wc -l
    @grep -rn 'subprocess\.run\|subprocess\.Popen\|subprocess\.call' scripts/*.py | grep -v 'run_cmd\|#.*subprocess\|test_\|def run_cmd\|ToolError' | head -20

# Modal script lint (NO_STAGE, SUBPROCESS_UNCHECKED, vol lifecycle, threads)
[group('quality')]
lint-modal:
    uv run python scripts/lint_modal_scripts.py

# Run both validation planes. Use this for full local readiness, not for
# deciding whether a refactor's code/architecture work is closed.
[group('quality')]
validate: validate-code validate-data

# Code-focused validation: contracts, invariants, lint, and static repo checks.
# This is the closeout/merge signal for code and architecture work.
[group('quality')]
validate-code: type-check-core lint-silent-fallbacks lint-template-strings repo-contracts report-contracts canary ir-canary verify-genotypes bio-verify-validate scientific-claim-validate retraction-gate lint-imports lint-product-imports lint-architecture check-codebase-map check-claude-md lint-docs lint-phenotype-contract

# Data/output validation: sample-dependent checks against current local artifacts.
# This reports sample readiness and may stay red when local artifacts are absent
# even if validate-code is green.
[group('quality')]
validate-data: smoke evidence-preflight prs-sanity spotcheck snapshot-check schema-check registry-qc verify-convergence

# Canonical preflight for refactor/architecture closeout:
# refresh generated count-bearing docs, then run the code-focused closeout gate.
[group('quality')]
plan-close-preflight: sync-generated-docs validate-code
    @echo "plan-close-preflight: validate-code passed"
    @echo "Run 'just validate-data' separately for sample-readiness telemetry."

# Canonical post-implementation review entrypoint using one combined context
# packet from the actual worktree diff and touched files.
[group('quality')]
plan-close-review topic="plan close review" question="Review the actual diff and touched files for correctness, silent failures, edge cases, and migration overclaim.":
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .model-review
    packet=".model-review/plan-close-context.md"
    uv run python3 ~/Projects/skills/review/scripts/build_plan_close_context.py --repo "$(pwd)" --output "$packet"
    uv run python3 ~/Projects/skills/review/scripts/model-review.py --context "$packet" --topic "{{topic}}" --project "$(pwd)" --extract --verify "{{question}}"

# Scientific-claim governance gate for the active governed slice
[group('quality')]
scientific-claim-validate:
    uv run python3 scripts/lint_claim_governance.py
    uv run python3 scripts/claim_governance_preflight.py --check --materialize-trait-stage
    uv run python3 scripts/inventory_scientific_claims.py --check

# Rebuild supported scientific-claim governance surfaces and repo-wide inventory
[group('quality')]
scientific-claim-build *ARGS:
    uv run python3 scripts/build_scientific_claim_governance.py {{ARGS}}

# Inventory scientific-claim-bearing surfaces across config and scripts
[group('quality')]
scientific-claim-inventory *ARGS:
    uv run python3 scripts/inventory_scientific_claims.py {{ARGS}}

# Advisory audit for suspicious DOI/title mappings on governed trait rows
[group('quality')]
scientific-claim-audit-sources *ARGS:
    uv run python3 scripts/audit_trait_panel_sources.py {{ARGS}}

# Verify convergence report claims against source stage data (advisory — non-fatal)
[group('quality')]
verify-convergence:
    uv run python scripts/verify_convergence.py --json | uv run python -c "import sys,json; d=json.load(sys.stdin); v=d.get('fully_verified',0); t=d.get('convergence_genes_total',0); print(f'Convergence: {v}/{t} verified'); sys.exit(0)"

# Retraction propagation gate (DAG integrity + dependency closure)
[group('quality')]
retraction-gate:
    uv run python scripts/test_retraction_propagation.py

# Check database version ledger freshness
[group('quality')]
version-check:
    uv run python scripts/version_check.py

# Full QA suite (validate + drift + gold + versions)
[group('quality')]
qa-full: validate drift-check gold-check version-check
    @echo "Full QA suite passed"

# Check CLAUDE.md facts and key repo-count docs against codebase reality
[group('quality')]
check-claude-md:
    uv run python3 scripts/validate_claude_md.py

# Auto-fix stale CLAUDE.md facts and key repo-count docs
[group('quality')]
fix-claude-md:
    uv run python3 scripts/validate_claude_md.py --fix

# Refresh generated repo docs/count surfaces in one explicit repair step
[group('quality')]
sync-generated-docs:
    uv run python3 scripts/sync_generated_docs.py

# Regenerate codebase-map.md from current scripts
[group('quality')]
regen-codebase-map:
    uv run python3 scripts/gen_codebase_map.py

# Check codebase-map staleness
[group('quality')]
check-codebase-map:
    uv run python3 scripts/gen_codebase_map.py --check

# ── Control Plane ─────────────────────────────────────────────────

# Validate concept registry consistency
[group('quality')]
concept-validate:
    uv run python3 scripts/conceptctl.py validate

# Validate shared plan index consistency
[group('quality')]
plan-validate:
    uv run python3 scripts/planctl.py validate

# Validate both concept and plan control planes
[group('quality')]
control-plane-validate: concept-validate plan-validate

# Rebuild concept registry from discovery ledger
[group('quality')]
concept-sync:
    uv run python3 scripts/conceptctl.py sync

# Refresh plan index outputs
[group('quality')]
plan-sync:
    uv run python3 scripts/planctl.py sync

# ── Pipeline Stages ───────────────────────────────────────────────

# Pipeline orchestrator — show execution plan
[group('pipeline')]
pipeline-plan *ARGS:
    uv run python3 scripts/pipeline_orchestrator.py plan {{ARGS}}

# Pipeline orchestrator — compile without launching
[group('pipeline')]
pipeline-dry-run *ARGS:
    uv run python3 scripts/pipeline_orchestrator.py dry-run {{ARGS}}

# Pipeline orchestrator — execute stages
[group('pipeline')]
pipeline-run *ARGS:
    find scripts/ -name "*.pyc" -delete 2>/dev/null
    uv run python3 scripts/pipeline_orchestrator.py run {{ARGS}}

# Pipeline orchestrator — DV VCF re-run
[group('pipeline')]
pipeline-rerun-vcf:
    uv run python3 scripts/pipeline_orchestrator.py run --vcf-rerun

# Pipeline orchestrator — initialize control-plane schema
[group('pipeline')]
pipeline-db-init:
    uv run python3 scripts/pipeline_orchestrator.py db-init

# Pipeline orchestrator — import durable receipts into the control plane
[group('pipeline')]
pipeline-backfill *ARGS:
    uv run python3 scripts/pipeline_orchestrator.py backfill {{ARGS}}

# Pipeline orchestrator — show current DB-backed run state
[group('pipeline')]
pipeline-status:
    uv run python3 scripts/pipeline_orchestrator.py status

# Modal billing by stage (today, yesterday, or custom range)
[group('pipeline')]
modal-cost RANGE="today":
    uv run python3 -m modal billing report --for {{RANGE}} --tag-names stage --json | \
    uv run python3 scripts/modal_cost_report.py

# What's stale and why?
[group('pipeline')]
stale *ARGS:
    uv run python3 scripts/freshness.py {{ARGS}}

# Why is a specific stage stale?
[group('pipeline')]
why stage:
    uv run python3 scripts/freshness.py --why {{stage}}

# What breaks if a stage is stale?
[group('pipeline')]
downstream stage:
    uv run python3 scripts/freshness.py --downstream {{stage}}

# Impact of recent code changes (also: `just stale --from-git HEAD~5`)
[group('pipeline')]
impact *ARGS:
    uv run python3 scripts/impact_analysis.py {{ARGS}}

# Probe a modal script's image (build + sandbox validation)
[group('pipeline')]
probe stage:
    uv run python3 scripts/modal_probe.py "$(uv run python3 scripts/pipeline_cli.py script {{stage}})"

# Run a pipeline stage (auto-probes image build first)
[group('pipeline')]
run stage:
    uv run python3 scripts/modal_probe.py "$(uv run python3 scripts/pipeline_cli.py script {{stage}})" --build-only
    uv run python -m modal run "$(uv run python3 scripts/pipeline_cli.py modal-target {{stage}})"

# Run a pipeline stage without probe (escape hatch)
[group('pipeline')]
run-raw stage:
    uv run python -m modal run "$(uv run python3 scripts/pipeline_cli.py modal-target {{stage}})"

# Run a pipeline stage in background (detached)
[group('pipeline')]
run-detach stage:
    uv run python3 scripts/modal_probe.py "$(uv run python3 scripts/pipeline_cli.py script {{stage}})" --build-only
    uv run python -m modal run --detach "$(uv run python3 scripts/pipeline_cli.py modal-target {{stage}})"

# Watch Modal volume for results and download
[group('pipeline')]
download-results remote pattern dest:
    uv run python scripts/modal_watch_results.py --remote {{remote}} --pattern "{{pattern}}" --download --dest {{dest}}

# ── Variant Triage ────────────────────────────────────────────────

# Generate variant review packets (JSON)
[group('analysis')]
review-packets:
    uv run python scripts/generate_review_packets.py

# Calibrate auto-classification against gold standard
[group('analysis')]
calibrate:
    uv run python scripts/calibrate_auto_class.py

# ── Reporting ─────────────────────────────────────────────────────

# Generate unified report (Markdown)
[group('analysis')]
report:
    uv run python scripts/generate_report_md.py

# Generate report to specific output file
[group('analysis')]
report-out out:
    uv run python scripts/generate_report_md.py -o {{out}}

# Post-expansion review — run after sessions with 5+ new scripts
[group('quality')]
expansion-review:
    #!/usr/bin/env bash
    set -euo pipefail
    NEW_FILES=$(git diff --name-only --diff-filter=A HEAD~20 -- 'scripts/*.py' | wc -l | tr -d ' ')
    echo "New scripts in last 20 commits: $NEW_FILES"
    echo "── Running validate ──"
    just validate
    echo ""
    echo "── Contract tests ──"
    uv run pytest tests/test_report_contracts.py -v
    echo ""
    if (( NEW_FILES >= 5 )); then
        echo "⚠ $NEW_FILES new scripts — consider running /model-review on recent additions"
        git diff --name-only --diff-filter=A HEAD~20 -- 'scripts/*.py'
    else
        echo "✓ Below expansion threshold ($NEW_FILES < 5)"
    fi

# ── Testing & Quality ─────────────────────────────────────────────

# Probe all modal script images (build only — fast)
[group('quality')]
probe-all:
    uv run python3 scripts/modal_probe.py --all --build-only

# Nightly image sweep — build every unique Modal image to catch upstream breakage
[group('quality')]
image-sweep:
    uv run python3 scripts/image_sweep.py --skip-maturity-negative

# Run all tests
[group('quality')]
test:
    uv run pytest -v

# Bio-verify coverage status (all files with bio claims)
[group('quality')]
bio-verify-status:
    uv run python scripts/bio_verify_status.py

# Bio-verify priority queue (next 5 for /maintain)
[group('quality')]
bio-verify-queue:
    uv run python scripts/bio_verify_status.py --queue

# Bio-verify Tier 0 typed validators (variant_registry, gene_panels, etc.)
[group('quality')]
bio-verify-validate:
    uv run python scripts/bio_verify_validate.py

# ClinVar reclassification watch — diff live ClinVar against stored state
[group('quality')]
clinvar-watch:
    uv run python scripts/clinvar_watch.py

# ClinVar watch summary (no API calls)
[group('quality')]
clinvar-watch-summary:
    uv run python scripts/clinvar_watch.py --summary

# Verification ledger — per-variant, per-claim coverage dashboard
[group('quality')]
verify-status:
    uv run python scripts/verification_ledger.py --summary

# Rebuild verification ledger from batch_verify + clinvar_watch reports
[group('quality')]
verify-sync:
    uv run python scripts/verification_ledger.py --sync

# Lint Python code
[group('quality')]
lint:
    uv run ruff check scripts/ tests/

# Format Python code
[group('quality')]
fmt:
    uv run ruff format scripts/ tests/

# Check formatting without changes
[group('quality')]
fmt-check:
    uv run ruff format --check scripts/ tests/

# Pre-commit dry run — all blocking checks without committing
# Runs: ruff, architecture lint, json.dump ratchet, codebase-map freshness, canary
# Use this to iterate on fixes before `git commit` triggers the full hook chain
[group('quality')]
precheck:
    @echo "[1/5] ruff..."
    uv run ruff check scripts/ tests/
    @echo "[2/5] architecture lint..."
    uv run python scripts/lint_architecture.py
    @echo "[3/5] ratchet tests (json.dump, subprocess)..."
    uv run python -m pytest tests/test_repo_contracts.py -x -q --no-header 2>&1 | tail -3
    @echo "[4/5] codebase-map freshness..."
    just check-codebase-map
    @echo "[5/5] canary gate..."
    just canary
    @echo "✓ All pre-commit checks pass"

```
```
