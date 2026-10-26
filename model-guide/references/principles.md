# Model-selection principles: full wording

<!-- moved-from model-guide/SKILL.md L13-24 2026-10-26 -->
## Principles (full wording with evidence) (moved verbatim from SKILL.md)

> Moved verbatim from model-guide/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Principles

1. **Use the cheapest model and effort that passes the task's verifier.** The verifier in the brief sets the tier, not how hard the task feels. A gated brief licenses a cheap executor, and a gate-less brief makes your review the gate ([Dispatch Economics](references/dispatch-economics.md)).
2. **On a subscription every tier costs $0, so choose by quality and plan headroom. On a metered API, choose the cheapest tier that passes.** Claude runs on the subscription only. Metered Anthropic API use needs an explicit request, because a metered lane can never beat a $0 lane on cost.
3. **Route only to the Pareto frontier: retire dominated models and migrate their callers.** A dominated id left in an allowlist gets picked by accident. llmx keeps retired prices for historical cost accounting.
4. **Effort is a per-model dial that you tune against the verifier. Never switch to a weaker model as a fix.** Effort names do not carry across models (Opus 5.5 at `low` collapses on research). Tools and in-loop checks scale test-time compute better than extra thinking (code and web access took Opus 5.5 from 69.8 to 180.1 on the Endless Exam, arXiv:2609.24555). More effort on a poorly calibrated model tends to buy longer confident errors ([trilemma](references/selection-trilemma.md)).
5. **Use cross-model review for consequential judgment. A model grading its own output is not review.** A second diverse pass is worth running because it finds issues the first missed. The measured gain from a different lab over a second same-lab instance is about zero, but you must still check any facts a reviewer asserts ([review pattern](references/cross-model-review.md)).
6. **Facts come from tools, not model recall.** Every model card shows factuality limits. When a model has to judge without a source, choose it for calibration (willingness to abstain) over index rank or size, and require an execution receipt for computed numbers.
7. **Probe the live transport and read back the served model before trusting config.** An alias or a successful dry-run proves configuration only, aliases move on release day, and a self-report is not proof ([transport](references/transport.md)).
8. **Vendor benchmarks are claims. Check `~/Projects/evals/DECISIONS.md` before any bake-off.** A fresh n=1 probe must not overturn a question an eval already settled. Treat CursorBench as contaminated until shown otherwise.
9. **Route classifier niches by exact id.** Opus 5.5 re-routes most cyber work to Opus 4.8 and declines dual-use biology, so that work goes to `claude-opus-5` by exact id.
10. **Work the principal verifies (taste, voice, conviction) stays with the operator.** Models draft and critique, but a model judge does not make taste verifiable.
