<!-- Reference file for llmx-guide skill. Loaded on demand. Rewritten 2026-10-26 (operator: "newest models always"; "no more deepinfra ... lithos is the goat"). Older rows live in git history. -->

# Model Names, Limits & Reasoning

Ids, prices and context windows below come from llmx (`usage_report.PRICING`, `CONTEXT_WINDOW`, `providers.MODEL_RESTRICTIONS`) on 2026-10-26. Rederive with `llmx info` before trusting a number here.

## Newest picks (default unless an eval pins otherwise)

| Model | llmx name | $/MTok in/out (API) | Effort | Route |
|---|---|---|---|---|
| GPT-6.1 Sol | `gpt-6.1-sol` | $2 / $10 | `low`…`max` (`none`/`minimal` → low) | `-p codex-cli --subscription` ($0) or API. `gpt-6-sol` aliases to it; needs codex-cli ≥ 0.162 |
| GPT-6 Astra | `gpt-6-astra` (alias `gpt-6`) | $10 / $50 | `low`…`max` (`none`/`minimal` → low) | **Default OpenAI / Codex model.** `--subscription` codex-cli ($0). Pro = `reasoning.mode=pro` (same rates) |
| Claude Opus 5.5 | `claude-opus-5-5` | $4 / $20 (metered only on explicit request) | `low`…`max`; per-task levels in `/model-guide` | `--subscription` (default); never `anthropic-direct` unasked |
| Gemini 4 Argon | `gemini-4-argon` | $2 / $10 intro through 2026-11-30, then $4/$20 | `low`/`medium`/`high` only (`minimal` → 400; `none`/`xhigh`/`max` → 400) | Metered API (`GEMINI_API_KEY_METERED`), `--flex` for 50% off. Temperature fixed at 1.0 |

`-p google` with no `-m` (and `llmx vision`, `llmx batch`) still defaults to `gemini-3.8-flash`: pass `-m gemini-4-argon` explicitly.

## Other current models

| Model | llmx name | $/MTok in/out | Notes |
|---|---|---|---|
| GPT-6 Luna | `gpt-6-luna` | $0.10 / $0.50 | Cheapest GPT; effort `none`…`max` |
| Claude Fable 5.1 | `claude-fable-5-1` | $10 / $50 | `--subscription` only; never fall back to paid API |
| Claude Opus 5 | `claude-opus-5` | $5 / $25 | Exact id for cyber / dual-use biology work (Opus 5.5 classifier niches) |
| Claude Sonnet 5 / Haiku 4.5 | `claude-sonnet-5`, `claude-haiku-4-5` | | Not on the subscription allowlist; `anthropic-direct` (metered) or the Agent tool |
| Grok 4.7 (Cursor pool) | `grok-4.7-{low,medium,high,xhigh}[-fast]` | subscription | **No `cursor-` prefix**; effort is in the slug, `-e` is ignored. Rederive with `cursor-agent models` |
| Grok 4.7 (Grok Build / xAI) | `grok-4.7` | $2 / $6 | `llmx chat -p grok -m grok-4.7 -e low\|medium\|high\|xhigh`; 500K context. xAI API 403 "key blocked" = key status |
| Kimi K3 | `kimi-k3` | $3 / $15 | `-p kimi`, metered; max-thinking server-side; temperature 1.0 |
| GLM-5.2 | `glm-5.2` | | `-p zai` (OpenRouter); effort `high`/`xhigh` only |
| Qwen 3.8 27B | `cerebras/qwen-3.8-27b` | $0.99 / $1.49 | `-p cerebras`; `-e none` for minimum latency; 131K context |

## DeepSeek V4.1 Flash — LithosAI only

`llmx chat -p lithosai` (key `LITHOSAI_API_KEY`, endpoint `api.lithosai.cloud/v1`, transport `lithosai-api`). Tiers are separate model ids, not a knob; every tier serves the same V4.1 Flash weights with a 1M context.

| Tier | `-m` alias (needs `-p lithosai`) | Wire id | $/MTok in/out | Measured decode (2026-10-24, effort high) |
|---|---|---|---|---|
| base (default) | `deepseek-flash` | `deepseek-ai/DeepSeek-V4.1-Flash` | $0.15 / $0.60 | 92 t/s |
| fast | `deepseek-flash-fast` | `deepseek-ai/DeepSeek-V4.1-Flash-fast` | $0.25 / $1.00 | 123 t/s |
| ultra | `deepseek-flash-ultra` (`-ultrafast` aliases it) | `deepseek-ai/DeepSeek-V4.1-Flash-ultra` | $0.35 / $1.40 | 288 t/s |

- Prices are LithosAI's early-access rate (half list); cached input bills at 2%, reasoning at the output rate.
- Thinking defaults to `high`; `-e none` turns it off; the full ladder `none`…`max` passes through.
- `-ultra` returns 429 "the model is at capacity" under concurrent calls (2 of 6 calls, 2026-10-24/25): keep parallel fan-out on base or `-fast`.
- `-ultra-chat` exists ($0.35/$1.40) but measured a 10.6 s time to first token: don't route to it.
- Prompt caching is automatic server-side; never send `promptCacheKey` (the API returns 400).
- Bare wire ids (`deepseek-ai/…`) and the `lithosai/` prefix route to LithosAI without `-p`; the short aliases do not (bare `deepseek-flash` goes to the DeepSeek platform provider).
- **DeepInfra is retired (2026-10-26).** `-p deepinfra` exits 2 "Unknown provider"; `deepinfra/…` model ids exit 2 `retired_model`. Old usage rows still price.
- Agentic work: `lane run <name> --repo <path> --brief <file> --worker opencode` (default model LithosAI base; `LANE_OPENCODE_MODEL=lithosai/deepseek-ai/DeepSeek-V4.1-Flash-ultra` for speed; exit 86 = balance exhausted, never retry).

## Older / pinned only

`gemini-3.8-flash` ($0.75/$3.75 intro; still the `-p google`/vision/batch default), `gemini-3.1-pro-preview` (explicit `-m` one-offs only; retired from routing 2026-06-13), `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` (priced, not routed), `deepseek-flash` on the DeepSeek platform (`-p deepseek`, peak-rate priced $0.30/$1.20).

**Refused by llmx (exit 2 `retired_model`, successor named):** every `gpt-5*` id, `gemini-3-flash-preview`, `gemini-3.5/3.6/3.7-flash`, `gemini-3-pro-preview`, `grok-4`, `grok-4.5`, `grok-4.6` / `cursor-grok-4.6-*`, `grok-4.20-*`, `grok-4-1-fast-*`, `claude-fable-5`, `claude-opus-4-8`, `composer-2.5(-fast)`. Full map: `llmx/model_ids.py` `RETIRED_API_MODELS`.

## Image models

| Model | llmx name | Notes |
|---|---|---|
| GPT Image 2 | `gpt-image-2` | Default for `llmx image`; generation and edit/reference |
| Gemini 3 Pro Image | `gemini-3-pro-image-preview` | `llmx image --provider google -m pro` |

## Name format and 404 traps

- No provider prefixes needed (`gemini-4-argon`, not `gemini/gemini-4-argon`); LiteLLM-style prefixes still parse with a deprecation warning.
- Hyphens, not dots, for Claude (`claude-opus-5-5`); dots for GPT (`gpt-6.1-sol`).
- A typo gets a closest-match suggestion ("did you mean …?").
- Grok 4.7 Cursor slugs have no `cursor-` prefix; `cursor-grok-4.7-*` does not exist.

## Limits and effort quirks

| Model | Max input | Max output | Notes |
|---|---|---|---|
| GPT-6.1 Sol / Astra / Luna | 1,050,000 | 128,000 | 2× input / 1.5× output price above 272K input |
| Claude Opus 5.5 / Fable 5.1 | 1,000,000 | | Subscription: omit `--max-tokens` (the CLI rejects it) |
| Gemini 4 Argon | 1,048,576 | | No prompt-length price tiers |
| Gemini 3.x | 1,000,000 | 65,536 | Server default output is 8K: pass `--max-tokens 65536` for long outputs |
| DeepSeek V4.1 Flash (LithosAI) | 1,048,576 | | |
| Grok 4.7 | 500,000 | | |

Google uses `thinking_config.thinking_level`, not `reasoning_effort`; llmx translates `-e` per provider. Temperature is pinned to 1.0 for Gemini thinking models, Kimi K3 and GLM-5.2.

OpenRouter occasionally streams empty `choices`; llmx guards it (an `IndexError` on `choices[0]` means an old llmx).
