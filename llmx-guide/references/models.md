## OpenAI — GPT-5.6 suite (GA 2026-07-09)

| ID | Role | $/MTok in/out | Effort |
|---|---|---|---|
| `gpt-5.6-sol` (alias `gpt-5.6`) | Flagship | $5 / $30 | none…max |
| `gpt-5.6-terra` | Balanced (≈ prior 5.5) | $2.50 / $15 | none…max |
| `gpt-5.6-luna` | Cheap/fast | $1 / $6 | none…max |

Default provider model: **Sol**. Pro = `reasoning.mode=pro` (same rates). Context 1.05M / 128K out.

<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Model Names, Limits & Reasoning

## Model Names & Defaults

| Model | llmx name | Notes |
|-------|-----------|-------|
| ~~Gemini 3.1 Pro~~ | `gemini-3.1-pro-preview` | **RETIRED as a routing option 2026-06-13 (operator).** Do not route here — flash-3.5 dominates critique/synthesis and is cheaper/faster (re-confirmed on the ADR-0009 spine critique). Still callable via explicit `-m` for a one-off ARC-AGI-2/GPQA/video need, but it is not a default or recommended pick anywhere. Paid API; free Gemini CLI retired 2026-05-31. |
| Gemini 3.5 Flash | `gemini-3.5-flash` | **Default Gemini for critique/synthesis** (promoted over 3.1 Pro 2026-05-24). Stable GA (May 2026). ~3× Flash pricing — Pro-lite tier. Paid API only (~$1.50/$9 per MTok; `--flex` = 50% off) — free Gemini CLI retired 2026-05-31. |
| Gemini 3 Flash | `gemini-3-flash-preview` | Cheap workhorse. `-preview` required. Use for high-volume classification, not when 3.5's reasoning is needed |
| GPT Image 2 | `gpt-image-2` | Current SoTA image model. Default for `llmx image`; supports generation and edit/reference workflows |
| Gemini 3 Pro Image | `gemini-3-pro-image-preview` | Available via `llmx image --provider google -m pro` |
| GPT-5.3 Instant | `gpt-5.3-chat-latest` | Reasoning max: **medium only**. Auto-defaults |
| GPT-5.6 Sol | `gpt-5.6-sol` (alias `gpt-5.6`) | **Default OpenAI model.** Flagship. $5/$30. Effort `none`…`max`. Pro = API `reasoning.mode=pro`. Context 1.05M / 128K. |
| GPT-5.6 Terra | `gpt-5.6-terra` | Mid opt-in. $2.50/$15. Effort `none`…`max`. |
| GPT-5.6 Luna | `gpt-5.6-luna` | **Everyday GPT** (≈ prior 5.5 perf at ~½ price). $1/$6. Also mechanical at low effort. |
| GPT-5.4 | `gpt-5.4` | Older GPT. Prefer Sol/Terra/Luna for new work. |
| GPT-5.2 (legacy) | `gpt-5.2` | Legacy OpenAI default. |
| GPT-5-Codex | `gpt-5-codex` | No `minimal` reasoning-effort |
| Claude Sonnet 5 | `claude-sonnet-5` | Released 2026-06-30. 1M context, 128K output, $3/$15 per MTok ($2/$10 intro through 2026-08-31). Adaptive thinking on by default; first Sonnet-tier model with `xhigh` effort. Not yet in `lite_allowed_models` (subscription allowlist) — `--subscription -m claude-sonnet-5` will not route until that's added. See `/model-guide` for routing guidance and the full system-card digest. |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Hyphens, not dots. Superseded by Sonnet 5 (2026-06-30) — prefer the newer ID for new work. |
| GLM-5.2 | `glm-5.2` | Z.ai via OpenRouter (`zai` provider). **Reasoning: high/xhigh only** (no low tier). Opt-in critique cosigner — see `/model-guide` trilemma + `agent-infra/decisions/2026-06-19-glm-5.2-integration.md`. |
| **Grok 4.5** (SpaceXAI, 2026-07-08) | `grok-4.5` | **Current xAI default** (`-p xai`). API: $2/$6 per MTok, 500k context, reasoning `low`/`medium`/`high` (default high). Live smoke may 403 with `API key is currently blocked` — key status, not geo (US egress still blocked 2026-07-09). Prefer Cursor pool / critique `grok` axis. |
| Grok 4.5 (Cursor pool) | `cursor-grok-4.5-{low,medium,high}` / `cursor-grok-4.5-{low,medium,high}-fast` | Exact live Cursor registry slugs (2026-07-14); effort precedes the optional `-fast` suffix and there is no xhigh slug. Route via `--subscription -m cursor-grok-4.5-high`. Bare `grok-4.5` remains the xAI API model. |
| Grok 4.20 Reasoning | `grok-4.20-0309-reasoning` | Legacy. Use `-p xai`. **Not in `_RECOMMENDED_MODELS`** — pass full name explicitly. |
| Grok 4.20 Non-Reasoning | `grok-4.20-0309-non-reasoning` | Latency tier, same backbone/price |
| Grok 4.20 Multi-Agent | `grok-4.20-multi-agent-0309` | `reasoning.effort` controls **agent count** (low/med→4, high/xhigh→16), not depth |
| Grok 4 (legacy default) | `grok-4` | Superseded by Grok 4.5 as llmx xAI default (2026-07-09) |
| Grok 4.1 Fast (cheap tier) | `grok-4-1-fast-reasoning` | xAI fast/cheap tier, still current |

**Model name format (v0.6.0+):** No provider prefixes needed. Use `gemini-3.5-flash` not `gemini/gemini-3.5-flash`. Old LiteLLM-style prefixed names (`gemini/`, `openai/`) still accepted with deprecation warning. Will be removed in a future version.

**Model name suggestions:** If you typo a model name, llmx suggests the closest match: `"gemini-3.5-flsh not found; did you mean gemini-3.5-flash?"`

**404 traps:** `gemini-3-flash` (missing `-preview`), `gemini-flash-3` (wrong order), `gpt-5.3` (needs `-chat-latest` suffix).

## Token Limits

| Model | Max Input | Max Output | Notes |
|-------|----------|-----------|-------|
| GPT-5.6 Sol / Terra / Luna | 1,050,000 | 128,000 | Effort includes `max`; Pro = `reasoning.mode=pro` |
| GPT-5.4 | 1,050,000 | 128,000 | |
| GPT-5.2 | 272,000 | 128,000 | |
| GPT-5.3 Chat | 128,000 | 16,384 | Smallest output cap — watch for truncation |
| o4-mini | 200,000 | 100,000 | |
| Gemini 3.1 Pro | 1,048,576 | 65,536 | Server default is 8K — always pass `--max-tokens 65536` |
| Gemini 3.5 Flash | 1,048,576 | 65,536 | Same window as Pro; pass `--max-tokens 65536` for long outputs |
| Gemini 3 Flash | 1,048,576 | 65,535 | |
| Grok 4.5 | 500,000 | (API default) | docs.x.ai Chat API table 2026-07-09 |
| Grok 4.20 Reasoning | 2,000,000 | 128,000 | **>200K input → 20× price tier** ($40/$120 per M). Chunk before crossing. |

## Reasoning Effort Values

| Model | Valid values | Default |
|-------|------------|---------|
| GPT-5.3 Instant | **medium only** | medium (auto) |
| GPT-5.6 Sol / Terra / Luna | none, low, medium, high, xhigh, **max** | medium |
| GPT-5.4 | none, minimal, low, medium, high, xhigh | high |
| GPT-5.2 | minimal, low, medium, high | high |
| GPT-5-Codex | low, medium, high | high |
| Gemini 3 Flash | low, medium, high | high (server-side, via `thinking_config`) |
| Gemini 3.5 Flash | low, medium, high | high (server-side, via `thinking_config`) |
| Gemini 3.x (Pro/Flash) | low, medium, high | high (server-side, via `thinking_config`) |
| Grok 4.5 (API) | **low, medium, high** | high |
| Grok 4.5 (Cursor) | effort baked into exact slug (`-low`/`-medium`/`-high`; optional trailing `-fast`) | pass an exact `cursor-grok-4.5-*` registry slug |
| Grok 4.20 Reasoning | **NONE — passing `reasoning_effort` errors** | auto (model reasons internally) |
| Grok 4.20 Multi-Agent | low, medium, high, xhigh — **selects agent count, not depth** (low/med→4 agents, high/xhigh→16) | -- |
| Grok 4.20 Non-Reasoning | n/a (no thinking) | -- |

Temperature locked to 1.0 for GPT-5 and Gemini 3.x thinking models.

**Google API note:** Google uses `thinking_config` with `thinking_level` (not `reasoning_effort`) under the hood. llmx translates `--reasoning-effort` to the correct parameter per provider — you don't need to know this unless debugging raw API calls.

**OpenRouter streaming guard (v0.6.0+):** OpenRouter occasionally sends empty `choices` arrays in streaming chunks. llmx now guards against this — if you see `IndexError` on `choices[0]` in older versions, upgrade.

## Judge Names ≠ Model Names

| Context | Name |
|---------|------|
| llmx CLI | `gemini-3.5-flash` |
| tournament MCP judges | `gemini25-pro` |
