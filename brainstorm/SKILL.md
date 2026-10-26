---
name: brainstorm
description: "Use when: /brainstorm, divergent design space, denial/domain/constraint perturbation. Optional multi-model volume. NOT convergent review (/critique) or decisions (/decide)."
argument-hint: "[--quick|--deep] [--axes denial,domain,constraint,contradiction,blend] [--domains 'jazz, geology, ...'] [--n-ideas N] design space to explore"
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

**Core mechanism:** systematic perturbation, not model diversity; the prompting structure does the work. Use both dimensions:
- **Content-space** — denial cascade, domain forcing, constraint inversion, TRIZ contradiction, conceptual blending (moves *where* you look).
- **Output-distribution** — verbalized sampling (Step 2), always on; composes with every axis.

**This skill is DIVERGENT only.** It produces candidate space and coverage artifacts, not final selections or implementation plans. For convergent critique, use `/critique`.

Full wording, citations and incident evidence for everything below: `references/process-full.md`. Read it when a step's one-liner leaves you unsure how to run it, or before changing this skill.

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
| `--axes` | comma-separated: `denial`, `domain`, `constraint`, `contradiction`, `blend` | `denial,domain,constraint` | Run only specified perturbation axes. `contradiction` and `blend` are opt-in (auto-included by `--deep`). |
| `--domains` | quoted comma-separated domain names | auto-select | Override domain forcing domains (e.g., `--domains "jazz, geology, packet switching"`) |
| `--n-ideas` | integer | 15 | Target idea count per generation round |
| `--no-llmx` | — | off | Run everything locally, no external dispatch |

**Effort presets:** default (2 denial, 3 domains, 3 inversions, ~15/round), `--quick` (1 denial, 2 domains, no inversions, ~5/round), `--deep` (3 denial, 4 domains, 4 inversions, plus contradiction and blend rounds, ~20/round).

## Prerequisites

- Shared external-dispatch helper optional — skill works without it (you run all rounds). With external dispatch, perturbation rounds run in parallel for speed. Use `--no-llmx` to force local-only.

## Pre-Flight

1. **Dedup check:** Search `.brainstorm/` for synthesis.md files < 24h old on same topic. Check `git log` for cross-session brainstorms. If space already explored, target "one non-duplicate survivor or clean exhaustion proof."
2. **Goals & governance check:** Find `docs/GOALS.md`. Inject as preamble so generation stays within project principles.
3. **Packet setup:** Reuse the shared packet spine for topic, goals/governance, recent incidents, and prior brainstorm artifacts. Do not hand-roll an unbounded context blob when the packet builder exists.
4. **Output setup:** Create `$BRAINSTORM_DIR` with date-slug-id naming.

See `references/synthesis-templates.md` for pre-flight scripts.

## The Process

### Step 1: Define the Design Space

State clearly: the question, current approach (if any), hard constraints vs soft preferences, evaluation criteria.

**Reformulate before generating:** write 3 distinct constructions of the problem (different goal, obstacle or constraint set; "where do we get a jack?" vs "how do we raise the car?") and generate against at least two. `--quick` on a well-specified task may skip this.

### Step 2: Initial Generation

- **In-conversation first, dispatch second.** Generate `$N_IDEAS` approaches as plain text BEFORE any external dispatch (≥5 required by Mode Discipline). No evaluation yet; volume and diversity over brilliance. If the user gave seed ideas, diversify from there.
- **Stratify first:** in one planning pass name 4–6 broad, mutually distant semantic *directions* (not ideas), then fill each. Record them; they seed the `domain_row`/paradigm columns.
  - *Interface/API/module preset:* **minimize the interface**, **maximize flexibility**, **optimize the common caller**, **ports & adapters**. Stratify by constraint; do NOT spawn one agent per direction.
- **Verbalized sampling with an originality goal:** say "optimize for originality, not the most effective or expected answer", and ask for "N genuinely different approaches **and your probability/confidence for each**". Keep the probabilities in the raw artifact; they are NOT a ranking signal.
- **External dispatch** (optional): only AFTER your own set exists, for volume/availability, not diversity (parallel fan-out converges). Payloads, Multi-Output default, persona constraints: `references/llmx-dispatch.md`. **Do not poll** the output file; wait for the completion signal (process exit, marker file), then read once.

### Step 3: Perturbation Rounds (The Core Mechanism)

Run axes from `--axes` (default `denial,domain,constraint`; `contradiction` and `blend` when named or under `--deep`); fan out in parallel with external dispatch, else sequentially. First name the 3-5 dominant paradigms from Step 2: these are what you escape.

- **3a: Denial Cascade** — ban dominant paradigms, force different approaches; the primary divergence mechanism. Round 1 always also bans "bridge/connect X and Y" and "unify/integrate existing approaches". Pass paradigm *labels*, never example idea text. Payloads: `references/llmx-dispatch.md`.
- **3b: Domain Forcing** — map the problem to unrelated domains from `references/domain-pools.md`: one mid-distance domain (shares function or relational structure, not vocabulary), the rest far.
- **3c: Constraint Inversion** — flip key assumptions (e.g., "compute free but storage costs $1/byte"), design for the altered world, identify what transfers back. Skipped in `--quick`.
- **3d: Contradiction (TRIZ)** — opt-in. Name "improve X without worsening Y" pairs explicitly first (infra decisions usually are one: depth vs maintenance surface, autonomy vs blast radius, context richness vs token cost); per pair pull 3-5 principles from `references/triz-principles.md`, one idea per principle applied to the actual system. A resolution dissolves the contradiction; picking a point on the X/Y curve fails the round.
- **3e: Conceptual Blending** — opt-in. Force-merge TWO frames: state each frame's roles/relations/dynamics, map counterparts, describe the blend as one system, keep ONLY emergent structure. Discard straight A→B transfers (that's 3b) and "unify A and B". No emergent structure → record the dry cell in `coverage.json`.

**Knowledge injection:** before perturbation, query 2-3 tangential domain examples via Exa; prefer less-common source examples.

**Mature frontier cutoff:** after one forced-domain pass on a mature frontier, discard duplicates/no-caller ideas; don't keep forcing domains.

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

Sections: Ideas to Explore, Parked, Rejected, Paradigm Gaps, Suggested Next Step. **Select by gate, then spread; never by novelty × feasibility:** gate each idea on feasibility and soundness, then take the largest set of survivors that differ on a core mechanism, ordered by feasibility. Judge novelty only against a reference (Step 2 paradigms, prior `.brainstorm/` runs) and ask whether each idea is narrow or source-bound; don't trust your own novelty ratings or pairwise comparison. Save to `$BRAINSTORM_DIR/synthesis.md`; template in `references/synthesis-templates.md`.

### Step 5.5: Pain-Point Gate (MANDATORY before implementation)

Before offering to plan or implement ANY explore item, verify it solves a real problem:

1. `git log --oneline --all | grep -i "<topic keywords>"` — actual incidents
2. `grep -r "<topic>" ~/.claude/projects/*/memory/` — session pain moments
3. For each EXPLORE item: "This would have prevented [specific incident] on [date]"
4. If no incident: mark `SPECULATIVE` in disposition. Default to PARK, not EXPLORE.

This gate exists to populate `caller_evidence`, `speculative`, and final disposition support. It is not a convergent review pass and should not turn brainstorm into a findings engine. Absence of a feature ≠ presence of a problem.

### Step 6: Bridge to Action

If EXPLORE items survive the pain-point gate:

> "Brainstorm identified N ideas worth exploring (M survived pain-point gate). Want a plan for the top 1-2, or `/critique` to stress-test a specific idea?"

Don't auto-implement — divergent ideas need convergent validation first.

## Anti-Patterns

- **Evaluating during generation.** Steps 2-3 generate. Steps 4-5 evaluate. Don't mix.
- **Skipping denial rounds.** Initial generation IS the attractor basin. Denial is how you escape it.
- **All-adjacent domains for domain forcing.** Adjacent fields converge to the same basin. One mid-distance domain is deliberate; the rest are far.
- **Implementing brainstorm output directly.** Prototype cheaply or stress-test with `/critique` first.
- **Skipping coverage artifacts.** If you cannot name the matrix cells you covered, you do not yet know what was actually explored.
- **Using brainstorm as a decision memo.** It produces candidate space plus coverage, not the final call.
- **Synthesizing without extracting.** Drops ideas silently. Always extract first.
- **Treating model choice or parallel fan-out as the diversity mechanism.** Agent count is for volume and availability only (verifier-gated fork loops are different; brainstorm has no grader).
- **Using expert/authority personas during generation.** "Senior scientist" framing suppresses semantic diversity. Generate with independent/neutral framing; bring expertise in at the convergent (`/critique`) stage.

## Reference Files

| File | Contents |
|------|----------|
| `references/llmx-dispatch.md` | Shared dispatch prompt payloads, packet expectations, and artifact contract |
| `references/domain-pools.md` | Domain forcing pools, perturbation axis presets, knowledge injection details |
| `references/triz-principles.md` | 40 inventive principles (agent/software glosses) + contradiction-pair routing table for the contradiction axis |
| `references/synthesis-templates.md` | Matrix, coverage, disposition table, synthesis output template, pre-flight bash scripts |
| `references/process-full.md` | Full wording of the mechanism, Mode Discipline rationale, process steps and anti-patterns, with citations and incident evidence |

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Duplicate runs — brainstorm dispatched 3x to same model when parallel subagent calls failed silently. Check subagent output before re-dispatching.**
- **[2026-04-18] Codex/GPT-5.4 bypassed entire skill body in 8/8 automated genomics sessions** — defaulted to `rg`/`sed`/`wc` loops to find missing implementations and converged to "single survivor" without any divergent generation. Polled background `domain-forcing.md` 11x while still being written. Mode Discipline gate added to head of skill on this date as architectural mitigation. Sessions: 019d9ff9, 019da0d4, 019da08d, 019da11b, 019da165, 019da1a1, 019da1d8, 019da210. Evidence: `agent-infra/research/brainstorm-codex-execution-failure-2026-04-18.md` and `agent-infra/improvement-log.md` 2026-04-18 entry.
