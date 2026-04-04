---
name: brainstorm
description: Divergent ideation via systematic perturbation — denial cascades, domain forcing, constraint inversion. Multi-model dispatch optional (volume, not diversity). For convergent critique, use /model-review.
argument-hint: "[--quick|--deep] [--axes denial,domain,constraint] [--domains 'jazz, geology, ...'] [--n-ideas N] design space to explore"
effort: high
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
---

# Divergent Ideation via Perturbation

You are orchestrating divergent ideation. The goal is ideas that escape the default attractor basin — the high-probability outputs that any model (including you) produces first.

**Core mechanism:** Systematic perturbation of the search space (denial, domain forcing, constraint inversion), not model diversity. Models trained on similar data converge on similar ideas regardless of vendor. The prompting structure does the work.

**This skill is DIVERGENT only.** For convergent critique, use `/model-review`.

**Late-stage warning:** When a frontier is mature, this skill should produce fewer, sharper ideas, not preserve the same idea count with weaker variants. One strong perturbation survivor is enough. If forced-domain rounds only yield reframings, stop and hand back to convergent filtering.

## Parameters

Parse `$ARGUMENTS` for these optional flags (order doesn't matter, remaining text is the topic):

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--quick` | — | off | 1 denial round, 2 domains, skip constraint inversion. ~5 ideas. |
| `--deep` | — | off | 3 denial rounds, 4 domains, 4 inversions. Maximum divergence. |
| `--axes` | comma-separated: `denial`, `domain`, `constraint` | all three | Run only specified perturbation axes |
| `--domains` | quoted comma-separated domain names | auto-select | Override domain forcing domains (e.g., `--domains "jazz, geology, packet switching"`) |
| `--n-ideas` | integer | 15 | Target idea count per generation round |
| `--no-llmx` | — | off | Run everything locally, no external model dispatch |

**Effort presets:** default (2 denial, 3 domains, 3 inversions, ~15/round), `--quick` (1 denial, 2 domains, no inversions, ~5/round), `--deep` (3 denial, 4 domains, 4 inversions, ~20/round).

## Prerequisites

- `llmx` CLI optional — skill works without it (you run all rounds). With llmx, perturbation rounds run in parallel for speed. Use `--no-llmx` to force local-only.

## Pre-Flight

1. **Dedup check:** Search `.brainstorm/` for synthesis.md files < 24h old on same topic. Check `git log` for cross-session brainstorms. If space already explored, target "one non-duplicate survivor or clean exhaustion proof."
2. **Constitutional check:** Find CONSTITUTION.md or constitution section in CLAUDE.md + GOALS.md. Inject as preamble so generation stays within project principles.
3. **Output setup:** Create `$BRAINSTORM_DIR` with date-slug-id naming.

See `references/synthesis-templates.md` for pre-flight scripts.

## The Process

### Step 1: Define the Design Space

State clearly: the question, current approach (if any), hard constraints vs soft preferences, evaluation criteria.

### Step 2: Initial Generation

Generate `$N_IDEAS` approaches. Cast wide — no evaluation yet. Optimize for volume and diversity over individual brilliance — research confirms LLMs are competitive with humans on creative volume but not at distribution extremes (Nature Human Behaviour 2025). More seeds = more raw material for perturbation. If user included seed ideas, diversify from there.

With llmx: dispatch external model in parallel while generating your own set. See `references/llmx-dispatch.md` for templates.

### Step 3: Perturbation Rounds (The Core Mechanism)

Run axes specified by `--axes` (default: all three). With llmx, dispatch active axes in parallel (multiple Bash calls, `timeout: 360000`). Without llmx, run sequentially.

First: identify the 3-5 dominant paradigms from Step 2. These are what we're escaping.

**3a: Denial Cascade** — Ban dominant paradigms, force genuinely different approaches. Novelty rises continuously with denial depth (NEOGAUGE, NAACL 2025). This is the primary divergence mechanism. See `references/llmx-dispatch.md` for prompt templates.

**3b: Domain Forcing** — Map the problem to distant, unrelated domains. Pick from domain pools in `references/domain-pools.md`. Distant domains, not adjacent ones — the discomfort is the mechanism.

**3c: Constraint Inversion** — Flip key assumptions (e.g., "compute free but storage costs $1/byte"). Design optimal solutions under altered constraints, then identify what transfers back to reality. Skipped in `--quick` mode.

**Knowledge injection:** Before perturbation, query 2-3 tangential domain examples via Exa to prime the search space with real-world mechanisms.

**Mature frontier cutoff:** After one forced-domain pass on a mature frontier, discard duplicates/no-caller ideas, don't keep forcing more domains.

### Step 4: Extract & Enumerate (Anti-Loss Protocol)

**Do this BEFORE synthesis.** Single-pass synthesis drops ideas.

Mechanically extract every discrete idea from all artifacts into a numbered list tagged by source. Then build a disposition table: `EXPLORE`, `PARK`, `REJECT`, or `MERGE WITH [ID]`. Every extracted item must have a disposition. See `references/synthesis-templates.md` for table format and extraction scripts.

### Step 5: Synthesize

Produce ranked synthesis with: Ideas to Explore (novelty x feasibility), Parked, Rejected, Paradigm Gaps, Suggested Next Step. Save to `$BRAINSTORM_DIR/synthesis.md`. See `references/synthesis-templates.md` for output template.

### Step 5.5: Pain-Point Gate (MANDATORY before implementation)

Before offering to plan or implement ANY explore item, verify it solves a real problem:

1. `git log --oneline --all | grep -i "<topic keywords>"` — actual incidents
2. `grep -r "<topic>" ~/.claude/projects/*/memory/` — session pain moments
3. For each EXPLORE item: "This would have prevented [specific incident] on [date]"
4. If no incident: mark `SPECULATIVE` in disposition. Default to PARK, not EXPLORE.

**Why this exists:** Brainstorm session (2026-03-26) generated 47 ideas, 12 explored, 7 planned, 1 built. 6/7 layers defended against hypothetical problems with zero incident history. Absence of a feature ≠ presence of a problem.

### Step 6: Bridge to Action

If EXPLORE items survive the pain-point gate:

> "Brainstorm identified N ideas worth exploring (M survived pain-point gate). Want a plan for the top 1-2, or `/model-review` to stress-test a specific idea?"

Don't auto-implement — divergent ideas need convergent validation first.

## Anti-Patterns

- **Evaluating during generation.** Steps 2-3 generate. Steps 4-5 evaluate. Don't mix.
- **Skipping denial rounds.** Initial generation IS the attractor basin. Denial is how you escape it.
- **"Related" domains for domain forcing.** Adjacent fields converge to the same basin. Pick distant domains.
- **Implementing brainstorm output directly.** Prototype cheaply or stress-test with `/model-review` first.
- **Synthesizing without extracting.** Drops ideas silently. Always extract first.
- **Treating model choice as the diversity mechanism.** The prompting structure (denial, domains, inversions) produces divergence. Model choice is for volume and availability.

## Reference Files

| File | Contents |
|------|----------|
| `references/llmx-dispatch.md` | Prompt templates for all llmx calls (generation, denial, domain, constraint, extraction) |
| `references/domain-pools.md` | Domain forcing pools, perturbation axis presets, knowledge injection details |
| `references/synthesis-templates.md` | Disposition table format, synthesis output template, pre-flight bash scripts |

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Duplicate runs — brainstorm dispatched 3x to same model when parallel subagent calls failed silently. Check subagent output before re-dispatching.**
