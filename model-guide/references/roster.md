# Roster: full table with why each model is on the frontier

<!-- moved-from model-guide/SKILL.md L26-46 2026-10-26 -->
## Roster with frontier rationale (moved verbatim from SKILL.md)

> Moved verbatim from model-guide/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Roster (Pareto frontier, 2026-10-26)

Newest picks (operator 2026-10-26: "newest models always"): `gpt-6.1-sol`, `gpt-6-astra`, `claude-opus-5-5`, `gemini-4-argon`.

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
| [gemini-4-argon](references/models/gemini.md) | Default Gemini: critique Gemini axes (`arch`, `gaps`) since 2026-10-14 (operator), never the sole reviewer | Third-party knowledge-work lead (Vals Index #1) at about half Opus 5.5's cost; weak agentic coder; Google's own long-context numbers unreplicated | Metered API (`GEMINI_API_KEY_METERED`) |
| DeepSeek V4.1 Flash on LithosAI | Metered bulk and opencode `lane` work where price or wall time beats quality | Cheapest metered reasoning lane; same weights at three speeds (measured 2026-10-24, effort high: base 92 t/s, fast 123, ultra 288). Calibration unread for V4.1 Flash; DeepSeek V4 Pro abstained on only ~6% of misses (BENCHMARKS.md), so facts come from tools | `llmx -p lithosai -m deepseek-flash` / `-fast` / `-ultra` ($0.15/$0.60, $0.25/$1.00, $0.35/$1.40 early-access); opencode lanes |
| [GLM-5.2](references/models/glm-5-2.md) | Opt-in review cosigner and epistemic guardrail; not an extractor | Separate training lab; best measured calibration among routed models | OpenRouter/zai metered, `--axes …,glm` |
| [kimi-k3](references/models/kimi-k3.md) | Opt-in long-horizon coding probe | Open-weight model from a separate lab; cache-cheap repeated context | `llmx -p kimi` metered; Kimi Code CLI |

Older / pinned only: `gemini-3.8-flash` (cheap diverse reviewer; still llmx's `-p google`, vision and batch default), `gemini-3.1-pro-preview` (explicit `-m` one-offs), `gemini-3.5/3.1-flash-lite` (priced, not routed). DeepInfra retired 2026-10-26 (operator: "no more deepinfra ... lithos is the goat").

Retired 2026-09-25 (operator: allowlists hold the Pareto frontier only): every model not in this table; git history keeps their old guidance. Retired 2026-10-07 (operator: "outdated"): composer-2.5 and composer-2.5-fast; successor gpt-6-astra at `low` effort, with gpt-6.1-sol at `high` when Astra's plan limit binds.
