---
name: analyze
description: "Use when: why/root-cause, confounder, regression, ACH, DAG adjustment, weakest-link. Lenses: null, causal, dag, hypotheses, audit, stop. NOT ideation (/brainstorm)."
user-invocable: true
argument-hint: "[lens] [question or target]"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: high
---

# Analyze

Shared reasoning lens library. This skill recommends lenses; it does not own
project routing thresholds, domain evidence standards, or final workflow
decisions.

Project workflows decide:

- whether analysis is required
- which evidence threshold counts
- when a result changes a decision, falsifier, rerun, monitor, or research queue

## Lens Selection

| Lens | Use when | Load |
|---|---|---|
| null/base-rate | The observation may be normal, seasonal, sector-wide, or mean-reverting | `lenses/null-base-rate.md` |
| causal-attribution | The user asks why something happened or what caused a change | `lenses/causal-attribution.md` |
| dag-adjustment | Regression, controls, confounders, causal effect, bad controls | `lenses/dag-adjustment.md` |
| hypotheses-ach | Multiple explanations, fraud-vs-error, anomaly triage, adversarial workup | `lenses/hypotheses-ach.md` |
| weakest-link-audit | A causal story sounds plausible but may have one unsupported link | `lenses/weakest-link-audit.md` |
| spirit-audit | A work-product is judged against a contract (eval verdict, backtest, gate, benchmark, claim) and may be letter-true but spirit-false (gaming, invalid gold, errors-scored-as-results, confounds, leakage) | `lenses/spirit-audit.md` |
| decision-impact-stop | Analysis may not change any action | `lenses/decision-impact-stop.md` |

Detailed reference files remain under `references/` for DAG algorithms,
templates, worked examples, and ACH formats.

Adjunct: when the object under analysis is a published quantitative claim (a headline number, %, ranking, or model output), also run the construction checks — ledger, unit, base, window, gross/net, measurement-vs-model — from the research skill's `references/quant-bias-checklist.md` (32 items, historical anchors).

## Mode Recommendation

1. Define the observation precisely.
2. Run null/base-rate before causal story generation.
3. If residual remains:
   - shape-matched "why" question -> causal attribution
   - regression/control question -> DAG adjustment
   - 3+ live explanations -> hypotheses/ACH
   - plausible chain with uncertain mechanism -> weakest-link audit
4. If the result would not alter a decision, falsifier, monitor, data rerun, or
   research queue item, label it `NON-ACTIONABLE` and stop.

## Output Contract

Every analysis should end with:

- leading explanation or "null explains it"
- top alternative
- falsifier or discriminating evidence
- decision impact
- next action, or `NON-ACTIONABLE`

Do not use this shared skill to encode project-private alpha, donor/sample
context, private file paths, or domain-specific thresholds. Keep those adapters
inside the project workflow that invoked the lens.
