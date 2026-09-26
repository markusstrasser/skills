# Gemini — critique-only policy

> Moved from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Retired-model content pruned 2026-09-25 (git history keeps it). Source lines: L126-145, L162.

**Current policy (2026-07-14 ADR, `agent-infra/decisions/2026-07-14-gemini-critique-only-policy.md`):** Gemini is critique-only. llmx refuses `gemini-*` without `LLMX_GEMINI_OK=1`; the key is meant to live only as `GEMINI_API_KEY_CRITIQUE_ONLY`. Frontier ids (2026-09-25): `gemini-3.8-flash` (cosigner), `gemini-3.1-pro-preview` (explicit `-m` one-offs only), `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` (registered for pricing, not routed).

- **Flash-Lite pair is REGISTERED, NOT ROUTED.** `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` are in llmx only so the spend guard can price them. Prices (ai.google.dev pricing, 2026-07-22): 3.5 Flash-Lite **$0.30/$2.50**, 3.1 Flash-Lite **$0.25/$1.50**. Effort ladders probed live: 3.5-Flash-Lite accepts `minimal`, 3.1-Flash-Lite **rejects** it.
- **Do NOT reach for Flash-Lite as the cheap extraction lane — Astra-low on subscription (or `gpt-6-luna` metered) stays it.** GPT tiers are
  **$0 on the ChatGPT subscription**; Flash-Lite is metered under a policy that only permits
  /critique. A metered lane cannot beat a $0 lane on cost, so Flash-Lite would have to win big on
  quality, and our own screening probe says it does not (see below).

- **`gemini-3.1-pro-preview` is RETIRED as a routing option (2026-06-13, operator).** Do not route here for critique/synthesis/review — `gemini-3.8-flash` is the cosigner. (Benchmark records in `references/BENCHMARKS.md` are kept as evidence; this is a routing retirement, not a data scrub. Callable via explicit `-m` if a one-off ever needs ARC-AGI-2/GPQA/video, but it is not a default anywhere.)
