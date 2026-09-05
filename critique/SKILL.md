---
name: critique
description: "Use when: /critique, 'review plan', 'what's wrong', fact-check plans/findings/closeout. Modes: model, verify, close. NOT code diffs (/code-review) — critique owns design/plan layer."
user-invocable: true
argument-hint: <mode> [target]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Critique

Review plans and designs, verify model findings against code, or close an implemented plan. Select the mode before loading its workflow or dispatching reviewers.

## Choose the work

| Request or current artifact | Route | Read when selected |
|---|---|---|
| Diff, PR, or “review this diff” | `/code-review` only | The code-review skill; do not also critique the same diff |
| Explicit `model`, or a plan/design with no later state | `model` | [Adversarial review](lenses/adversarial-review.md) |
| Explicit `audit-plan`, or audit backlog (≥15 open items) plus remediation plan | `audit-plan` | [Repo audit plan review](lenses/repo-audit-plan-review.md) |
| Explicit `verify`, or findings/audit output with no plan | `verify` | [Verification](lenses/verification.md) |
| Explicit `close`, or a recent plan with implementation commits since plan start | `close` | [Plan close review](lenses/plan-close-review.md) |

Actual diff review always routes to code-review. For other artifacts, explicit modes take precedence; with no mode, check close, audit-plan, verify, and finally model.

**Choose the smaller workflow before reading further:**

- A single specific bug: inspect the code directly. Scientific or external factual claims: use `/research`. Already human-verified findings need no standalone verification pass.
- Skip the close workflow for trivial plans (<30 lines, one function, obvious correctness), research/analysis that produces no code, and config/data-only changes with no logic changes. Use the checks appropriate to the artifact.
- Audit-plan is the repo-inventory workflow: fresh same-session lane evidence can be reused; otherwise its first audit pass requires repo lanes before critics. It is not the default for an ordinary plan.
- Model review is convergent. Use `/brainstorm` for divergent ideation. Extra cosigners, formal review, and broader presets are conditional choices in the selected workflow, not automatic additions.

## Shared review contracts

- **One pass per layer:** `review_targets.diff_target` belongs to code-review; `design_target` belongs to critique. Honor `dispatch.json` layer ownership and blockers. A closeout may need both layers, once each.
- **Manifest-driven dispatch:** assemble the actual review packet, run `review_gate.py triage`, then pass its matching `--dispatch-manifest` to `model-review.py`. Explicit CLI flags override manifest fields; do not reuse another packet's manifest. Exact commands, provenance, valid `repo|packet` scopes, and budget rules: [Dispatch](references/dispatch.md).
- **Ground repo premises:** a plan depending on live callers, schemas, or joins needs repo evidence before packet-only critics. The premise scout supplies this in normal repo reviews; self-contained packets may disable it. Declare target users, current/designed scale, and rate of change. Include only current governance relevant to this review: [Context assembly](references/context-assembly.md).
- **Preserve the evidence:** read every axis output and account for every extracted finding. Inspect `coverage.json` for packet provenance, dispatch coverage, and extraction/verification totals. `verified-disposition.md` checks anchors and local corroboration; it is not semantic proof.
- **Verify before acting:** model agreement and self-reported confidence do not establish truth. Confirm code behavior or external facts at their sources. Fix all confirmed/corrected findings within the authorized scope; give a reason per deferred item. Preserve genuine judgment disagreements for the user.
- **Migration stance:** default to full caller migration and deletion of old paths. Any retained compatibility boundary needs a live consumer, reason, and removal condition.

## Supporting references

Load only the reference needed for the selected task:

- [Dispatch](references/dispatch.md): axes, transports, subscription constraints, packet manifests, artifact contracts, and failures.
- [Context assembly](references/context-assembly.md): gathering patterns, scope, and context biases.
- [Extraction](references/extraction.md): manual extraction, complete disposition, and multi-round coverage.
- [Prompts](references/prompts.md): custom prompt templates; the script owns default prompts.
- [Biases and anti-patterns](references/biases-and-antipatterns.md): interpreting reviewer errors and disagreements.
- [Known issues](references/known-issues.md): read when debugging dispatch; append new incidents here or through `~/Projects/skills/hooks/append-skill-memento.sh critique '<one-line issue>'`.
- [History and calibration](references/history.md): preserved rationale and superseded routing; consult for provenance, not current instructions.

$ARGUMENTS
