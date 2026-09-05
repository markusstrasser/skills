<!-- Model-mode workflow. Load only after selecting model review. -->

# Adversarial Review

Use this for convergent critique of a plan or design. Actual diffs belong to `/code-review`; adding a model axis is not an alternate diff-review route.

## Select scope and cost

Keep a bounded, self-contained review as one packet. Split a broad review into 2–4 independent subparts by phase, module cluster, concern, or risk tier; use a tight packet for each (<80KB is the existing soft target). The parent merges findings across subparts.

Run deterministic triage before choosing a larger model panel. Triage recommends the preset from scope and evidence; do not overwrite that choice with an automatic four-axis pass. The CLI fallback and preset definitions, optional cosigners, and transport limits are in [Dispatch](../references/dispatch.md).

- Formal/math/Bayes/proof/invariant subparts may add `formal`; perceived importance alone is not an effort-escalation reason.
- Domain-dense packets may add `domain`; larger structural reviews may use `deep`.
- Extra `composer`, `claude`, `glm`, or `grok` cosigners are opt-in for a specific need. Composer is packet-only here and is excluded from closeout design; the diff layer already owns its review.
- `full` includes the divergent `alternatives` axis. Select it only when alternatives are part of the requested work and keep that output separate from convergent findings.
- Repo-scale audit inventories with remediation plans use [Audit-plan](repo-audit-plan-review.md), including its lane-evidence prerequisite and lean critics.

## Assemble and dispatch

Read [Context assembly](../references/context-assembly.md) to build the actual packet. Include a `## Scope` block with target users, current and designed-for scale, and data rate of change. Include enough code/caller evidence to test the plan's premises. Curate governance only when current and relevant; blind adversarial review is the default.

For repo-backed subparts, the packet builder can select exact files:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" --file path/a.py --file path/b.py \
  --output .model-review/subpart-1-context.md

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo "$(pwd)" --packet .model-review/subpart-1-context.md --mode model

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --dispatch-manifest .model-review/dispatch.json \
  --context .model-review/subpart-1-context.md \
  --topic "$TOPIC — subpart 1" --project "$(pwd)" \
  --question "Review this subpart's design and premises. Do not speculate about files absent from context."
```

The builder's sidecar separates diff and design review targets. Review only the design target here. Inspect triage's manifest before dispatch; stop on blockers. Re-triage each changed packet and use its matching manifest. [Dispatch](../references/dispatch.md) defines scope/scout options, profile timeouts, extraction, sibling roots, and coverage artifacts.

For plans with repo premises, keep repo-grounded premise verification before the packet-only axes. For an entirely self-contained packet, select `--context-scope packet` or the equivalent manifest policy instead of paying for an irrelevant scout.

## Read outputs, verify, and synthesize

Read every axis output, then merge raw extracted findings across all subparts. Never synthesize an earlier synthesis. Account for all items using [Extraction](../references/extraction.md) when manual work is needed.

Verify each code claim against actual files and behavior; search for a claimed missing feature and trace its callers. A plausible name, file anchor, or model agreement only locates evidence. Use [Verification](verification.md) for a full findings report.

| Bucket | Meaning | Action |
|---|---|---|
| Convergent | Reviewers independently flag the same issue | Verify, then fix if confirmed |
| Single-source | One reviewer flags an issue and another is silent | Verify; silence is a coverage gap, not disagreement |
| Divergent | Reviewers address the same decision and recommend incompatible answers | Resolve factual disputes with evidence; preserve genuine judgment choices for the user |

Cross-model agreement plus source verification is stronger than agreement alone. Contradiction by the actual code defeats a finding. Do not rank by raw model confidence. The script's confidence tiebreaker does not turn self-reported confidence into a calibrated probability; historical measurements are in [History](../references/history.md).

Before adopting a fix, identify where you disagree with reviewers and what context they lacked. Convergence on a flaw does not establish that their proposed fix is appropriately sized. See [Biases and anti-patterns](../references/biases-and-antipatterns.md) for recurrent failure patterns.

## Act and hand off

Apply verified convergent and single-source findings within the authorized task. Fix all confirmed/corrected items; defer only with a specific reason. The updated artifact is the deliverable when implementation is in scope. If every finding is rejected or deferred, deliver the disposition.

State genuine divergent recommendations with both positions and their implications; do not silently blend them or implement one while the user's decision is pending. A factual contradiction is resolved by verification, not by a vote.

Before closing, inspect `coverage.json` for packet drops, completed/failed axes, extraction totals, and verification totals. Preserve `shared-context.md`, its manifest, axis outputs, `findings.json`, `disposition.md`, and any `verified-disposition.md` in the script's review directory. Grounded anchor checks still require semantic review of the claim.

Historical default panels, calibration results, the genomics LR/math review note, and retired Fable instructions are preserved in [History](../references/history.md). They are not current transport authority.
