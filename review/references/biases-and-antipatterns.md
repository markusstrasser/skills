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
- **Gemini Pro:** Production-pattern bias (enterprise for personal projects), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.4:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep
- **Flash/GPT-5.3:** Shallow analysis (extraction only), recency bias. Never use for architectural judgment.

**Dispatch specifics:** the shared review contract owns provider routing,
timeouts, fallback, and artifact emission. This reference should track reviewer
biases and workflow anti-patterns, not raw transport flags.

## Anti-Patterns

- **Synthesizing without extracting.** #1 information loss. Always extract + disposition before prose.
- **Synthesizing a synthesis.** Each compression drops ideas. Merge raw extractions, not prior syntheses.
- **Adopting without code verification.** Both models hallucinated "missing" features that already existed.
- **Model agreement = proof.** Agreement is evidence, not proof — verify against source code.
- **Debate workflow.** Martingale. Independent parallel + voting beats sequential discussion.
- **Same-family reviewers.** Same-model correction: 59.1%. Cross-family: 90.4% (FINCH-ZK).
- **"Top N" triage.** If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section.** Most valuable part of each review.
- **Same prompt to both models.** Gemini = patterns, GPT = quantitative/formal. Different strengths need different prompts.
- **Writing to /tmp.** Persist to `.model-review/YYYY-MM-DD-topic/`.
- **Bare date directories.** Always append topic slug to avoid same-day collisions.
- **Skipping constitutional check.** Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming.** Convergent only. Use `/brainstorm` for divergent.
- **Priming tool names in review prompt.** Turns critique into evaluation. Use `alternatives` axis separately.
- **Scale-ambiguous context.** Both models converge on the same wrong answer from shared misleading context.
