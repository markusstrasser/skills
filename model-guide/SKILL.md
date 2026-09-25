---
name: model-guide
description: "Choose a model and effort by principle: the cheapest frontier model that passes the task's verifier, cross-lab review for consequential judgment, facts from tools. Pareto-frontier roster (Opus 5.5, GPT-6 Astra/Sol/Luna, Fable 5.1, Grok 4.7, opt-in lanes); per-model prompting in references. Transport flags: /llmx-guide."
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Choose a model and effort from the principles below, then read the model's reference file for prompting and watch-items. Transport mechanics belong to `/llmx-guide` and the live mirror `llmx info`.

## Principles

1. **Use the cheapest model and effort that passes the task's verifier.** The verifier in the brief sets the tier, not how hard the task feels. A gated brief licenses a cheap executor, and a gate-less brief makes your review the gate ([Dispatch Economics](references/dispatch-economics.md)).
2. **On a subscription every tier costs $0, so choose by quality and plan headroom. On a metered API, choose the cheapest tier that passes.** Claude runs on the subscription only. Metered Anthropic API use needs an explicit request, because a metered lane can never beat a $0 lane on cost.
3. **Route only to the Pareto frontier: retire dominated models and migrate their callers.** A dominated id left in an allowlist gets picked by accident. llmx keeps retired prices for historical cost accounting.
4. **Effort is a per-model dial that you tune against the verifier. Never switch to a weaker model as a fix.** Effort names do not carry across models (Opus 5.5 at `low` collapses on research). Tools and in-loop checks scale test-time compute better than extra thinking. More effort on a poorly calibrated model tends to buy longer confident errors ([trilemma](references/selection-trilemma.md)).
5. **Use cross-model review for consequential judgment. A model grading its own output is not review.** A second diverse pass is worth running because it finds issues the first missed. The measured gain from a different lab over a second same-lab instance is about zero, but you must still check any facts a reviewer asserts ([review pattern](references/cross-model-review.md)).
6. **Facts come from tools, not model recall.** Every model card shows factuality limits. When a model has to judge without a source, choose it for calibration (willingness to abstain) over index rank or size, and require an execution receipt for computed numbers.
7. **Probe the live transport and read back the served model before trusting config.** An alias or a successful dry-run proves configuration only, aliases move on release day, and a self-report is not proof ([transport](references/transport.md)).
8. **Vendor benchmarks are claims. Check `~/Projects/evals/DECISIONS.md` before any bake-off.** A fresh n=1 probe must not overturn a question an eval already settled. Treat CursorBench as contaminated until shown otherwise.
9. **Route classifier niches by exact id.** Opus 5.5 re-routes most cyber work to Opus 4.8 and declines dual-use biology, so that work goes to `claude-opus-5` by exact id.
10. **Work the principal verifies (taste, voice, conviction) stays with the operator.** Models draft and critique, but a model judge does not make taste verifiable.

## Roster (Pareto frontier, 2026-09-25)

| Model | Role | Why it is on the frontier | Transport |
|---|---|---|---|
| [claude-opus-5-5](references/models/claude-opus-5-5.md) | Default Claude: coding (`medium`), hard work (`xhigh`), architecture (`max`), research (`high`+) | Matches or beats Fable 5.1 on most card rows at 40% of the token price; best-calibrated Claude | Subscription: `opus` alias, Agent tool, `llmx --subscription` |
| [claude-fable-5-1](references/models/claude-fable-5-1.md) | Named-edge lane; the operator's interactive choice | Table reasoning edge; `low` effort holds up on research | Subscription (Max allowance), claude-cli |
| [claude-opus-5](references/models/claude-opus-5.md) | Cyber and dual-use biology work; lanes pinned to it | No bio classifier; 5.5 re-routes cyber | Subscription, exact id only |
| [claude-sonnet-5](references/models/claude-sonnet-5.md) | Cost tier: gated coding, no-gate mechanical work, injection-heavy input | Strongest prompt-injection robustness at a lower price than Opus | Agent tool / `claude -p`; not on the llmx subscription allowlist |
| claude-haiku-4-5 | Cheapest Claude for mechanical no-gate work | Lowest-cost Claude tier | Agent tool; llmx anthropic-direct |
| [gpt-6-astra](references/models/gpt-6-astra.md) | Default GPT: headless cheap lane at `low`, Codex implementation, cross-lab reviewer, quantitative work (pro mode) | Beats Luna at any effort on quality; $0 on the subscription | codex-cli subscription (`llmx --subscription`, `codex exec`) |
| [gpt-6-sol](references/models/gpt-6-sol-luna.md) | Metered mid tier; fallback when Astra's plan limit binds | Astra training at a lower serving cost | Codex subscription + API |
| [gpt-6-luna](references/models/gpt-6-sol-luna.md) | Metered bulk extraction and mechanical work | Cheapest GPT; replaced gpt-5.3 ("6 luna wins") | Codex subscription + API |
| [grok-4.7](references/models/grok-4-7.md) | Opt-in read-only repo critique axis; Grok Build headless | Separate lab with workspace access; cost and speed edge | cursor-agent `grok-4.7-<effort>[-fast]`; `grok` CLI; xAI API unverified |
| composer-2.5(-fast) | Built-in premise scout in `/critique` and `/code-review` | Repo-grounded caller and join checks by default | cursor-cli subscription |
| [gemini-3.8-flash](references/models/gemini.md) | Critique cosigner only, never the sole reviewer | Cheap diverse reviewer in the 2G+2GPT mix | Metered API, `LLMX_GEMINI_OK=1` |
| [gemini-3.1-pro-preview](references/models/gemini.md) | Explicit `-m` one-offs (ARC-AGI-2, GPQA, video) | Registered, not a default anywhere | Metered API |
| [gemini-3.5/3.1-flash-lite](references/models/gemini.md) | Registered for pricing, not routed | Lets the spend guard price them | Metered API |
| [GLM-5.2](references/models/glm-5-2.md) | Opt-in review cosigner and epistemic guardrail; not an extractor | Separate training lab; best measured calibration among routed models | OpenRouter/zai metered, `--axes …,glm` |
| [kimi-k3](references/models/kimi-k3.md) | Opt-in long-horizon coding probe | Open-weight model from a separate lab; cache-cheap repeated context | `llmx -p kimi` metered; Kimi Code CLI |

Retired 2026-09-25 (operator: allowlists hold the Pareto frontier only): the GPT-5.6 suite, GPT-5.4 and older including gpt-5.3, Fable 5, Opus 4.8 (Anthropic still uses it server-side as 5.5's cyber reroute), Grok ≤4.6, Gemini 3 and 3.5-3.7 Flash, and gemini-3-pro-preview. Their sections are kept as history: [GPT-5.6](references/gpt-5-6-suite.md), [Fable 5](references/fable-5-dormant.md), [Opus 4.8 card](references/opus-4-8-system-card.md).

## Settled operator decisions

- Claude runs on the subscription only; the metered API requires an explicit request.
- Architecture, design and high-reasoning critique use Opus `max` plus GPT-6 Astra, never Sonnet (2026-06-20). **Open:** whether Sonnet 5 changes that verdict is the operator's call ([details](references/models/claude-sonnet-5.md)).
- Allowlists hold the Pareto frontier only (2026-09-25). llmx refuses most retired ids, but `gpt-5.6-*` still dispatched on the API lane when probed that day ([known issues](references/known-issues.md)).
- Gemini is critique-only (2026-07-14 ADR); `gemini-3.1-pro-preview` was retired from routing on 2026-06-13.
- GLM-5.2 is an opt-in cosigner, not an extractor (2026-06-19).
- Moving the interactive setting off Fable 5.1 is the operator's call.
- `opus-low` is licensed for briefed, gated execution only; research and synthesis run at `medium` or higher.

## References

- Per-model specs, prompting and watch-items: [references/models/](references/models/). Prompting guides: [Claude](references/PROMPTING_CLAUDE.md), [GPT](references/PROMPTING_GPT.md).
- Choosing an executor tier (the "Dispatch Economics" section other skills cite): [dispatch-economics.md](references/dispatch-economics.md). Cosigner defaults: [cosigner-defaults.md](references/cosigner-defaults.md).
- Verified lanes and llmx facts: [transport.md](references/transport.md). Pre-rewrite routing tables: [routing-tables.md](references/routing-tables.md).
- Scores: [BENCHMARKS.md](references/BENCHMARKS.md). System-card digests: [Opus 5.5](references/opus-5-5-system-card.md), [Opus 5](references/opus-5-system-card.md), [Sonnet 5](references/sonnet-5-system-card.md).
- Checks after output: [validation-checklists.md](references/validation-checklists.md). Sources: [source-notes.md](references/source-notes.md). History: [CHANGELOG](references/CHANGELOG.md).

## When to Update This Skill

When a model is released or a system card is materially revised:
1. Read the model card, then add or update its `references/models/<slug>.md` file, `references/BENCHMARKS.md`, and the relevant prompting guide.
2. Update the roster row and register the id in llmx (`llmx info` must show it).
3. Prune the ids it dominates from llmx allowlists and the roster, and migrate every caller. Build a complete inventory first: count the matches (`rg -c`), then page through all of them.
4. Update [transport.md](references/transport.md) when a lane starts or stops serving the model it claims. Re-probe instead of assuming.
5. Add a dated entry to [CHANGELOG.md](references/CHANGELOG.md). Change the principles only when the evidence changes.

To log a defect or point of friction: `~/Projects/skills/hooks/append-skill-memento.sh model-guide '<one-line issue>'`.

## Known Issues

For matching failures, read [incident history](references/known-issues.md). The memento helper appends there.
