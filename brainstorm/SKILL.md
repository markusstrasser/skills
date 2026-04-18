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

**This skill is DIVERGENT only.** It produces candidate space and coverage artifacts, not final selections or implementation plans. For convergent critique, use `/model-review`.

## Mode Discipline (READ FIRST — gates everything below)

This skill is **GENERATIVE**, not analytical. It produces ideas that did not exist before the session started. It does NOT search the codebase to find what is missing.

**Forbidden during ideation phases (Steps 2 and 3):**
- `rg`, `grep`, `sed`, `awk`, `wc`, `find`, `cat`, `head`, `tail` to inspect caller code or "discover what to brainstorm about"
- `sleep N && check` polling loops on background dispatch output files
- Treating the absence of a feature in the codebase as a signal to add that feature (that's gap-analysis, a different task)
- Reading any file written by an in-flight `llmx`/external-dispatch process before completion is signalled — read once after the process exits, never poll
- Converging to "single survivor" before the disposition table exists

**Required before any tool call other than packet-build (Pre-Flight) and dispatch-launch:**
- Produce ≥5 candidate ideas as **plain text in the conversation**, with no tool use between them. This is non-negotiable. If you cannot generate 5 candidates from your own reasoning, the topic is under-specified — push back to the user, do not search the codebase to compensate.

**If you find yourself running `rg`/`grep`/`sed`/`wc` or polling files in this skill:** STOP. You are violating the contract. Re-enter divergent mode: write 5 raw ideas as conversation text, then continue from Step 3. This is not optional and is not advisory.

**Why this gate exists:** Codex/GPT-5.4 with the multi-MCP execution harness defaulted to `rg`/`sed` filtering loops in 8/8 automated brainstorm sessions on 2026-04-18 (genomics), ignoring the skill body entirely. HAIExplore v2 (arxiv 2512.18388, April 2026): execution-first interfaces cause premature convergence and design fixation. Architecture beats instructions — this section is the architecture.

**Late-stage warning:** When a frontier is mature, this skill should produce fewer, sharper ideas, not preserve the same idea count with weaker variants. One strong perturbation survivor is enough. If forced-domain rounds only yield reframings, stop and hand back to convergent filtering.

## Default Architectural Stance

Unless the user explicitly asks for compatibility, generate ideas as breaking refactors with full migration.

- Do not spend idea budget on wrappers, adapters, transitional bridges, or phased coexistence by default.
- Prefer ideas that delete obsolete paths and collapse complexity.
- Only keep a compatibility boundary in the design space when a live external dependency is explicitly named.

## Parameters

Parse `$ARGUMENTS` for these optional flags (order doesn't matter, remaining text is the topic):

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--quick` | — | off | 1 denial round, 2 domains, skip constraint inversion. ~5 ideas. |
| `--deep` | — | off | 3 denial rounds, 4 domains, 4 inversions. Maximum divergence. |
| `--axes` | comma-separated: `denial`, `domain`, `constraint` | all three | Run only specified perturbation axes |
| `--domains` | quoted comma-separated domain names | auto-select | Override domain forcing domains (e.g., `--domains "jazz, geology, packet switching"`) |
| `--n-ideas` | integer | 15 | Target idea count per generation round |
| `--no-llmx` | — | off | Run everything locally, no external dispatch |

**Effort presets:** default (2 denial, 3 domains, 3 inversions, ~15/round), `--quick` (1 denial, 2 domains, no inversions, ~5/round), `--deep` (3 denial, 4 domains, 4 inversions, ~20/round).

## Prerequisites

- Shared external-dispatch helper optional — skill works without it (you run all rounds). With external dispatch, perturbation rounds run in parallel for speed. Use `--no-llmx` to force local-only.

## Pre-Flight

1. **Dedup check:** Search `.brainstorm/` for synthesis.md files < 24h old on same topic. Check `git log` for cross-session brainstorms. If space already explored, target "one non-duplicate survivor or clean exhaustion proof."
2. **Constitutional check:** Find CONSTITUTION.md or constitution section in CLAUDE.md + GOALS.md. Inject as preamble so generation stays within project principles.
3. **Packet setup:** Reuse the shared packet spine for topic, constitution/goals, recent incidents, and prior brainstorm artifacts. Do not hand-roll an unbounded context blob when the packet builder exists.
4. **Output setup:** Create `$BRAINSTORM_DIR` with date-slug-id naming.

See `references/synthesis-templates.md` for pre-flight scripts.

## The Process

### Step 1: Define the Design Space

State clearly: the question, current approach (if any), hard constraints vs soft preferences, evaluation criteria.

### Step 2: Initial Generation

**In-conversation first, dispatch second.** Generate `$N_IDEAS` approaches as plain text in the conversation BEFORE launching any external dispatch. The Mode Discipline gate above requires this — at least 5 candidate ideas must exist as conversation text before any non-packet tool call. Cast wide — no evaluation yet. Optimize for volume and diversity over individual brilliance. More seeds = more raw material for perturbation. If user included seed ideas, diversify from there.

With external dispatch: AFTER your own in-conversation set exists, dispatch a parallel external pass for additional volume. See `references/llmx-dispatch.md` for prompt payloads and artifact contracts. **Do not poll** the dispatch output file — wait for the explicit completion signal (process exit, marker file), then read once.

### Step 3: Perturbation Rounds (The Core Mechanism)

Run axes specified by `--axes` (default: all three). With external dispatch, fan out active axes in parallel. Without it, run sequentially.

First: identify the 3-5 dominant paradigms from Step 2. These are what we're escaping.

**3a: Denial Cascade** — Ban dominant paradigms, force genuinely different approaches. Novelty rises continuously with denial depth (NEOGAUGE, NAACL 2025). This is the primary divergence mechanism. See `references/llmx-dispatch.md` for prompt payloads.

**3b: Domain Forcing** — Map the problem to distant, unrelated domains. Pick from domain pools in `references/domain-pools.md`. Distant domains, not adjacent ones — the discomfort is the mechanism.

**3c: Constraint Inversion** — Flip key assumptions (e.g., "compute free but storage costs $1/byte"). Design optimal solutions under altered constraints, then identify what transfers back to reality. Skipped in `--quick` mode.

**Knowledge injection:** Before perturbation, query 2-3 tangential domain examples via Exa to prime the search space with real-world mechanisms.

**Mature frontier cutoff:** After one forced-domain pass on a mature frontier, discard duplicates/no-caller ideas, don't keep forcing more domains.

### Step 3.5: Build Coverage Artifacts

Before synthesis, create the structured coverage artifacts first, then render the operator views:

- `$BRAINSTORM_DIR/matrix.json` — one row per idea/cell with axis, domain row, paradigm escaped, transfer mechanism, and disposition fields.
- `$BRAINSTORM_DIR/matrix.md` — rendered coverage table for operator review.
- `$BRAINSTORM_DIR/coverage.json` — requested axes, executed axes, counts, uncovered cells, merge counts, and mature-frontier stop reason.

If you cannot populate `matrix.json` without hand-waving, stop. The frontier is not covered enough to synthesize yet.

### Step 4: Extract & Enumerate (Anti-Loss Protocol)

**Do this BEFORE synthesis.** Single-pass synthesis drops ideas.

Mechanically extract every discrete idea from all artifacts into a numbered list tagged by source and matrix cell. Then build a disposition table: `EXPLORE`, `PARK`, `REJECT`, or `MERGE WITH [ID]`. Every extracted item must have a disposition, and the disposition table should render from the same `matrix.json` rows rather than becoming a second source of truth. See `references/synthesis-templates.md` for the matrix, coverage, and extraction templates.

### Step 5: Synthesize

Produce ranked synthesis with: Ideas to Explore (novelty x feasibility), Parked, Rejected, Paradigm Gaps, Suggested Next Step. Save to `$BRAINSTORM_DIR/synthesis.md`. See `references/synthesis-templates.md` for output template.

### Step 5.5: Pain-Point Gate (MANDATORY before implementation)

Before offering to plan or implement ANY explore item, verify it solves a real problem:

1. `git log --oneline --all | grep -i "<topic keywords>"` — actual incidents
2. `grep -r "<topic>" ~/.claude/projects/*/memory/` — session pain moments
3. For each EXPLORE item: "This would have prevented [specific incident] on [date]"
4. If no incident: mark `SPECULATIVE` in disposition. Default to PARK, not EXPLORE.

This gate exists to populate `caller_evidence`, `speculative`, and final disposition support. It is not a convergent review pass and should not turn brainstorm into a findings engine.

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
- **Skipping coverage artifacts.** If you cannot name the matrix cells you covered, you do not yet know what was actually explored.
- **Using brainstorm as a decision memo.** It produces candidate space plus coverage, not the final call.
- **Synthesizing without extracting.** Drops ideas silently. Always extract first.
- **Treating model choice as the diversity mechanism.** The prompting structure (denial, domains, inversions) produces divergence. Model choice is for volume and availability.

## Reference Files

| File | Contents |
|------|----------|
| `references/llmx-dispatch.md` | Shared dispatch prompt payloads, packet expectations, and artifact contract |
| `references/domain-pools.md` | Domain forcing pools, perturbation axis presets, knowledge injection details |
| `references/synthesis-templates.md` | Matrix, coverage, disposition table, synthesis output template, pre-flight bash scripts |

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Duplicate runs — brainstorm dispatched 3x to same model when parallel subagent calls failed silently. Check subagent output before re-dispatching.**
- **[2026-04-18] Codex/GPT-5.4 bypassed entire skill body in 8/8 automated genomics sessions** — defaulted to `rg`/`sed`/`wc` loops to find missing implementations and converged to "single survivor" without any divergent generation. Polled background `domain-forcing.md` 11x while still being written. Mode Discipline gate added to head of skill on this date as architectural mitigation. Sessions: 019d9ff9, 019da0d4, 019da08d, 019da11b, 019da165, 019da1a1, 019da1d8, 019da210. Evidence: `agent-infra/research/brainstorm-codex-execution-failure-2026-04-18.md` and `agent-infra/improvement-log.md` 2026-04-18 entry.
