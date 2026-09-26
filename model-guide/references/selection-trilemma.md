# Selection trilemma — capability × calibration × efficiency

> Moved from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Retired-model content pruned 2026-09-25 (git history keeps it). Source lines: L86-102.

## Selection trilemma (capability × calibration × efficiency)

Benchmark **capability** (Intelligence Index, SWE scores) and **parameter count** are weak proxies for real-world usefulness. They often **invert** on **calibration** — whether a miss is an abstention or a confident fabrication — and on **efficiency** — tokens/time to reach a correct or honest answer.

| Axis | What it measures | Routing mistake |
|---|---|---|
| **Capability** | Closed-set benchmark scores, index composites | Picking the #1 index model for every task |
| **Calibration** | Share of wrong answers that abstain vs confabulate (AA-Omniscience non-hallucination) | Treating critique reasoning as fact because the model is "smart" |
| **Efficiency** | Tokens, latency, $ to a verified outcome | Escalating reasoning effort on a poorly calibrated model |

**Calibration ordering (independent AA-Omniscience, misses only, abstention invited):** GLM-5.2 **72%** non-hallucination → DeepSeek V4 **~6%**. The current Claude, GPT-6 and Grok 4.7 lanes have no independent AA read yet; capability and calibration orderings were nearly reversed for their predecessors. A multi-trillion-parameter model can score at the top of an index and still be the worst choice when the task needs "I don't know" or detection of an impossible/contradictory spec.

**Opus 5.5 card (2026-09-22; Anthropic's own run on the AA-Omniscience public split, not comparable with the AA figures above):** incorrect 17% and abstain 7% (Mythos 5.1, the Fable 5.1 weights: 21% and 2%; Opus 5: 22% and 6%), so roughly 29% of its misses are abstentions against 9% for Mythos 5.1 [derived from rounded bar labels]. Within the Claude family it is the better-calibrated choice for unsourced facts; the AA ordering above stays the cross-lab reference until AA measures 5.5.

**Reasoning budget is not monotonic.** On badly calibrated models, more reasoning often buys longer confident wrong answers, not better ones. Anecdotal corroboration (Shrimpton 2026-06-18, n=1, high effort, temp 1): an impossible asyncio event-loop spec — DeepSeek V4 Pro ~7.7k reasoning tokens, 3m52s, full wrong implementation; GLM-5.2 ~800 tokens, 12s, correctly flagged the paradox. Don't throw `xhigh`/`max` at poorly calibrated GPT or DeepSeek for epistemic guardrails; use Opus, GLM (opt-in), or deterministic impossibility checks.

**Consumer rule:** match model to the axis that matters for the task — capability for gated mechanical work with a verifier; calibration for unsourced facts, paradox detection, and "should we even do this?"; efficiency for throughput. Never select on size or index rank alone.
