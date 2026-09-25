# Gemini — critique-only policy

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L126-145, L162.

**Current policy (2026-07-14 ADR, `agent-infra/decisions/2026-07-14-gemini-critique-only-policy.md`):** Gemini is critique-only. llmx refuses `gemini-*` without `LLMX_GEMINI_OK=1`; the key is meant to live only as `GEMINI_API_KEY_CRITIQUE_ONLY`. Frontier ids (2026-09-25): `gemini-3.8-flash` (cosigner), `gemini-3.1-pro-preview` (explicit `-m` one-offs only), `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` (registered for pricing, not routed). Gemini 3 / 3.5-3.7 Flash and `gemini-3-pro-preview` are retired 2026-09-25, Pareto-frontier prune (llmx refuses them).

- [historical: gemini-3.6-flash retired 2026-09-25, Pareto-frontier prune; 3.5 Flash-Lite stays registered] **Gemini 3.6 Flash / 3.5 Flash-Lite (launched 2026-07-21) are REGISTERED, NOT ROUTED (2026-07-22).**
  Live API ids `gemini-3.6-flash`, `gemini-3.5-flash-lite` (GA, no `-preview` suffix; verified
  against `models.list`, not guessed). Registered in llmx (`652d1ed`) purely so the spend guard
  stops refusing them as *unpriced* — **the 2026-07-14 critique-only policy is unchanged and no
  default moved.** Prices (verified at ai.google.dev/gemini-api/docs/pricing 2026-07-22):
  3.6 Flash **$1.50/$7.50**, 3.5 Flash-Lite **$0.30/$2.50**, 3.1 Flash-Lite **$0.25/$1.50**.
  Same pass corrected two badly stale entries — `gemini-3-flash` was priced in llmx at $0.075/$0.30
  against an actual **$0.50/$3.00**, so cost dashboards were understating Gemini ~7-10x. Note
  3.5 Flash-Lite is **6x input / 12.5x output the price of 3.1 Flash-Lite** — the "Lite" tier is no
  longer a rounding error. Effort ladders probed live: 3.5-Flash-Lite accepts `minimal`,
  3.1-Flash-Lite **rejects** it (do not pin `minimal` on the older one).
- **Do NOT reach for Flash-Lite as the cheap extraction lane — Astra-low on subscription (or `gpt-6-luna` metered) stays it.** GPT tiers are
  **$0 on the ChatGPT subscription**; Flash-Lite is metered under a policy that only permits
  /critique. A metered lane cannot beat a $0 lane on cost, so Flash-Lite would have to win big on
  quality, and our own screening probe says it does not (see below).
- [historical: resolved by the move to `gemini-3.8-flash` (2026-09-05); 3.5 and 3.6 Flash retired 2026-09-25, Pareto-frontier prune] **Open, operator's call — 3.6 Flash as the /critique cosigner in place of 3.5 Flash.** Strictly
  cheaper on the one lane Gemini is still allowed on: **$7.50 vs $9.00 output** *and* a vendor-claimed
  ~17% output-token reduction, i.e. roughly -30% on cosigner spend. NOT changed unilaterally — the
  `gemini-3.5-flash` cosigner default was set operator-empirical (2026-06-13, re-confirmed), and a
  vendor claim is not evidence that it reviews as well. Swap is one line in the critique axes.

- **`gemini-3.1-pro-preview` is RETIRED as a routing option (2026-06-13, operator).** Do not route here for critique/synthesis/review — flash-3.5 dominates and is cheaper/faster. (Benchmark records in `references/BENCHMARKS.md` are kept as evidence; this is a routing retirement, not a data scrub. Callable via explicit `-m` if a one-off ever needs ARC-AGI-2/GPQA/video, but it is not a default anywhere.)
