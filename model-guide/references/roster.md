# Roster: full table with why each model is on the frontier

<!-- moved-from model-guide/SKILL.md L26-46 2026-10-26 -->
## Roster with frontier rationale (moved verbatim from SKILL.md)

> Moved verbatim from model-guide/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Roster (Pareto frontier, 2026-09-25)

| Model | Role | Why it is on the frontier | Transport |
|---|---|---|---|
| [claude-opus-5-5](references/models/claude-opus-5-5.md) | Default Claude: coding (`medium`), hard work (`xhigh`), architecture (`max`), research (`high`+) | Matches or beats Fable 5.1 on most card rows at 40% of the token price; best-calibrated Claude | Subscription: `opus` alias, Agent tool, `llmx --subscription` |
| [claude-fable-5-1](references/models/claude-fable-5-1.md) | Named-edge lane; the operator's interactive choice | Table reasoning edge; `low` effort holds up on research | Subscription (Max allowance), claude-cli |
| [claude-opus-5](references/models/claude-opus-5.md) | Cyber and dual-use biology work; lanes pinned to it | No bio classifier; 5.5 re-routes cyber | Subscription, exact id only |
| [claude-sonnet-5](references/models/claude-sonnet-5.md) | Cost tier: gated coding, no-gate mechanical work, injection-heavy input | Strongest prompt-injection robustness at a lower price than Opus | Agent tool / `claude -p`; not on the llmx subscription allowlist |
| claude-haiku-4-5 | Cheapest Claude for mechanical no-gate work | Lowest-cost Claude tier | Agent tool; llmx anthropic-direct |
| [gpt-6-astra](references/models/gpt-6-astra.md) | Default GPT: headless cheap lane at `low` (incl. the `/critique` premise scout and `/diff-review` scout), Codex implementation, cross-lab reviewer, quantitative work (pro mode) | Beats Luna at any effort on quality; $0 on the subscription | codex-cli subscription (`llmx --subscription`, `codex exec`) |
| [gpt-6.1-sol](references/models/gpt-6.1-sol-luna.md) | Metered mid tier; fallback when Astra's plan limit binds | Astra training at a lower serving cost | Codex subscription + API |
| [gpt-6-luna](references/models/gpt-6.1-sol-luna.md) | Metered bulk extraction and mechanical work | Cheapest GPT ("6 luna wins") | Codex subscription + API |
| [grok-4.7](references/models/grok-4-7.md) | Opt-in read-only repo critique axis; Grok Build headless | Separate lab with workspace access; cost and speed edge | cursor-agent `grok-4.7-<effort>[-fast]`; `grok` CLI; xAI API unverified |
| [gemini-3.8-flash](references/models/gemini.md) | Search-grounded and vision dispatch; critique cosigner until 2026-10-14 | Cheap diverse reviewer | Metered API (`GEMINI_API_KEY_METERED`) |
| [gemini-4-argon](references/models/gemini.md) | Critique Gemini axes (`arch`, `gaps`) since 2026-10-14 (operator), never the sole reviewer | Third-party knowledge-work lead (Vals Index #1) at about half Opus 5.5's cost; weak agentic coder; Google's own long-context numbers unreplicated | Metered API (`GEMINI_API_KEY_METERED`) |
| [gemini-3.1-pro-preview](references/models/gemini.md) | Explicit `-m` one-offs (ARC-AGI-2, GPQA, video) | Registered, not a default anywhere | Metered API |
| [gemini-3.5/3.1-flash-lite](references/models/gemini.md) | Registered for pricing, not routed | Lets the spend guard price them | Metered API |
| [GLM-5.2](references/models/glm-5-2.md) | Opt-in review cosigner and epistemic guardrail; not an extractor | Separate training lab; best measured calibration among routed models | OpenRouter/zai metered, `--axes …,glm` |
| [kimi-k3](references/models/kimi-k3.md) | Opt-in long-horizon coding probe | Open-weight model from a separate lab; cache-cheap repeated context | `llmx -p kimi` metered; Kimi Code CLI |

Retired 2026-09-25 (operator: allowlists hold the Pareto frontier only): every model not in this table; git history keeps their old guidance. Retired 2026-10-07 (operator: "outdated"): composer-2.5 and composer-2.5-fast; successor gpt-6-astra at `low` effort, with gpt-6.1-sol at `high` when Astra's plan limit binds.
