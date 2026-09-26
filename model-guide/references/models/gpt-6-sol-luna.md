# GPT-6 Sol / Luna — OpenAI cost tiers

> Moved from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Retired-model content pruned 2026-09-25 (git history keeps it). Source lines: L276-289.

## GPT-6 Sol / Luna — OpenAI cost tiers (2026-09-22)

Same training methods as Astra, cheaper serving. Both on Codex/ChatGPT subscription (live `codex exec -m` and `llmx --subscription` probes 2026-09-25) and API.

| Tier | Model ID | $/MTok in/out | Role |
|---|---|---|---|
| **Sol** | `gpt-6-sol` | $2 / $10 | Metered mid tier; vendor: AutomationBench xhigh 33.2% beats Opus 5 max (26.9%) at 9% of its cost, FrontierCode ≈ Fable 5.1 xhigh |
| **Luna** | `gpt-6-luna` | $0.10 / $0.50 | Metered bulk extract / mechanical lane; vendor: DeepSWE max 66.6% ≈ Opus 5 medium |

**Specs (both):** 1.05M context, 128K output, effort `none|low|medium|high|xhigh|max` (default `medium`; unlike Astra, `none` is real). Cache reads 10%, writes 1.25×; >272K input bills 2× in / 1.5× out. Cutoffs: Sol 2026-04-20, Luna 2026-05-18. Source: openai.com/index/introducing-gpt-6-sol-and-luna, developers.openai.com/api/docs/models/gpt-6-{sol,luna}.

**Routing principle:** on the subscription every GPT tier is $0, so pick by quality and plan headroom — Astra by default, Sol/Luna when Astra's usage limit binds. On metered API, pick the cheapest tier that passes the task's verifier; Luna first for bulk. All numbers above are vendor-reported; no independent AA-Omniscience read yet, so GPT critique stays pressure on reasoning, not a fact source.
