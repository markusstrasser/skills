<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Known Model Biases & Anti-Patterns

## Systematic Biases

| Bias | Effect | Countermeasure |
|------|--------|----------------|
| **Correlated errors** | ~60% shared wrong answers when both err (Kim ICML 2025, pre-reasoning) | Never same-family reviewer + synthesizer |
| **Self-preference** | 74.9% demographic parity bias (Wataoka NeurIPS 2024) | Different-family synthesis; weight cross-family disagreements |
| **Judge inflation** | Same-provider accuracy inflation (Kim ICML 2025) | Cross-family only (this skill already does this) |
| **Debate = martingale** | Sequential discussion: no correctness improvement (Choi 2025, formal proof) | Independent parallel reviews, never let models respond to each other |

**Per-model:**
- **Gemini (3.5-flash):** Production-pattern bias (enterprise for personal projects), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.5:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep. **Calibration:** 14% AA-Omniscience non-hallucination (86% of misses are confident fabrications despite abstention invite) — worst among frontier models; do not escalate reasoning effort expecting better epistemic discipline.
- **GLM-5.2 (opt-in):** Best measured calibration among large routed models (72% non-hallucination, 2026-06-18); strong anecdotal impossibility/paradox detection. Expensive (`high`/`xhigh` only) — review cosigner, not default extractor or fact source.
- **DeepSeek V4 Pro:** ~6% non-hallucination — never cosigner or fact source; more reasoning tokens tends to lengthen wrong answers, not abstentions.
- **gemini-3-flash-preview / GPT-5.3:** Shallow analysis, ~42% hallucination as a critique axis — the cheap classification tier, never a cosigner. Distinct from gemini-3.5-flash, the clean primary cosigner.

**Dispatch specifics:** the shared review contract owns provider routing,
timeouts, fallback, and artifact emission. This reference should track reviewer
biases and workflow anti-patterns, not raw transport flags.

## Anti-Patterns

- **Synthesizing without extracting.** #1 information loss. Always extract + disposition before prose.
- **Synthesizing a synthesis.** Each compression drops ideas. Merge raw extractions, not prior syntheses.
- **Adopting without code verification.** Both models hallucinated "missing" features that already existed.
- **Model agreement = proof.** Agreement is evidence, not proof — verify against source code.
- **Convergence validates the problem, not the fix-size.** Cross-model agreement is the trust signal for *is this a real flaw* — it does NOT validate *is the proposed fix right-sized*. Both reviewers share a production-grade / more-machinery bias, so they converge on heavier solutions (new manifest, symlink, contract suite, extra service) exactly where a constraint you know about makes them unnecessary — and convergent over-engineering reads as high-confidence because convergence is normally the trust signal. Split the verdict: accept the flagged risk, then size the fix against constraints the models lacked. Evidence (phenome bridge-reframe, 2026-06-01): both models converged on an immutable release-manifest + `latest.json` symlink to fix a torn-snapshot risk; the affected artifacts were already co-located in one attempt, so a 2-line same-run check sufficed — adopting the convergent fix would have rebuilt the exact machinery the refactor was deleting.
- **Debate workflow.** Martingale. Independent parallel + voting beats sequential discussion.
- **Escalating reasoning on poorly calibrated models.** Higher effort on GPT-5.5 or DeepSeek for impossibility/contradiction detection or unsourced-fact review — produces longer confident wrong answers, not more abstention (Shrimpton 2026-06-18; see `/model-guide` trilemma). Use Opus, GLM opt-in, or deterministic checks instead.
- **Same-family reviewers.** Same-model correction: 59.1%. Cross-family: 90.4% (FINCH-ZK).
- **"Top N" triage.** If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section.** Most valuable part of each review.
- **Same prompt to both models.** Gemini = patterns, GPT = quantitative/formal. Different strengths need different prompts.
- **Writing to /tmp.** Persist to `.model-review/YYYY-MM-DD-topic/`.
- **Bare date directories.** Always append topic slug to avoid same-day collisions.
- **Skipping the goals/governance preamble.** Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming.** Convergent only. Use `/brainstorm` for divergent.
- **Auditing only the uncongenial side.** Mirror test: after compiling a failure list against an adversary's work, run the SAME list against your own artifacts in the same session. Generic "be rigorous" self-review finds nothing; a named external failure list found 4 real instances in one pass (research repo, 2026-06-11, Cato-study mirror). For content-level quantitative biases (ledgers, windows, bases, amplifiers — vs the review-process biases in this file), use the research skill's `references/quant-bias-checklist.md` as the verify-mode rubric.
- **Context-assembly biases** (scale ambiguity, priming alternatives/tool names, incumbent framing, missing boundary volumes / scope declaration…) — canonical table lives inline in SKILL.md § Context Anti-Patterns; not restated here.
- **Hand-applying model-suggested VALUE/IDENTIFIER corrections.** Models confidently "fix" specific tickers, function names, numbers, dates from stale training data. Evidence (intel 2026-06-01): a review flagged STMPA.PA/TKMS.DE/RSGN.SW as broken tickers at conf 0.70-0.90 — ground-truth (yfinance) proved 3 of 4 still price fine; hand-applying the "fixes" would have BROKEN valid symbols. Build/run a ground-truth check (the actual API/DB/file) before applying any concrete-value disposition. The validator IS the verification; the model's correction is a hypothesis.
- **Over-parameterization / composite-score-through-the-back-door.** A high-yield review axis for any signal/scoring/multi-factor plan: does it blend N signals into one number ("backtest A+B as a composite", "weighted score", "count of flags")? If the project bans aggregate scores, a composite validation reintroduces it covertly. Push for INDEPENDENT markers calibrated separately; intersections reported as named cohorts, not summed. Also ask "if forced to keep ONE signal and delete the rest, which survives?" — it exposes which signals are load-bearing vs ceremony. And "is the premise even real?" — a plan to surface names earlier assumes earlier surfacing yields better outcomes; demand the baseline test first.
