---
paths:
  - "docs/**"
  - "research/**"
  - "analysis/**"
---

# Research Protocol (Cross-Project Guidance)

Instruction-level guidance, not enforcement. Hooks enforce source grading (postwrite-source-check.sh)
and stop-gate (stop-research-gate.sh). This file shapes how research is conducted; hooks ensure
the output has provenance tags.

## Depth Routing

Route effort by stakes, not by default laziness. Domain-specific stakes are defined
per-project (see companion file in each project's `.claude/rules/`).

**HIGH** (per-domain critical decisions):
- Fetch and read at least one primary source (paper full text, filing, dataset query)
- Run one disconfirmation search ("X criticism", "X failed", "X replication")
- Self-grade all claims before writing
- Use `/competing-hypotheses` if single-hypothesis

**MEDIUM** (entity updates, methodology changes, research memos):
- At least one primary source OR one dataset query — no pure training-data synthesis
- One disconfirmation query

**LOW** (session notes, brainstorming, scratch work):
- Training data OK if labeled `[TRAINING-DATA]`
- No source obligations

## Stage Order

1. **Local knowledge audit** — what do we already know? Check existing docs, git history, substrate.
2. **Exploratory divergence** — multiple search axes, not just the first query that comes to mind.
3. **Hypothesis formation** — state falsifiable claims explicitly.
4. **Disconfirmation** (mandatory at HIGH/MEDIUM): actively search for contradictions.
5. **Claim-level verification** — every factual claim gets a provenance tag.
6. **Synthesis** — separate evidence from inference. Label each.

## Diminishing Returns Gate

Stop deepening and start writing when:
1. **Source convergence:** two independent sources agree and no contradictions found
2. **Marginal yield:** last research action added no new information
3. **Scope creep:** research expanding laterally instead of resolving the original question

Sufficient evidence for the stakes level beats exhaustive coverage.

## Primary Source Obligation (HIGH/MEDIUM)

Before citing a paper, fetch and read it. Abstracts are not primary sources.
Before citing a dataset, query it. "CMS data shows..." requires a SQL result.
Before citing a statistic, find the original measurement. Secondary citations decay.

## Disconfirmation Obligation (HIGH/MEDIUM)

For every key claim, search for contradictory evidence before finalizing.
Patterns: "X criticism", "X vs Y", "X failed", "X limitations".
If contradictory evidence exists, include it. If none found, say so explicitly.

## Blind First-Pass (for updates to existing analysis)

When evaluating new evidence on a topic where you have prior analysis:
1. Read the NEW evidence only. Do NOT read your prior analysis first.
2. Form an independent assessment from the evidence alone.
3. THEN read your prior analysis and compare.
4. If they diverge materially, document both assessments and reconcile explicitly.

Purpose: breaks commitment/consistency bias. The prior analysis is context, not a constraint.

## Domain-Specific Stakes Examples

Each project defines what counts as HIGH/MEDIUM/LOW in its own `.claude/rules/`:

- **intel:** >$10M leads = HIGH; entity updates = MEDIUM; brainstorming = LOW
- **genomics:** classification changes = HIGH; tool evaluation = MEDIUM; pipeline notes = LOW
- **selve:** health protocol changes = HIGH; literature review = MEDIUM; notes = LOW
- **meta:** architectural decisions = HIGH; improvement-log entries = MEDIUM; session notes = LOW
