<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Model Names, Limits & Reasoning

## Model Names & Defaults

| Model | llmx name | Notes |
|-------|-----------|-------|
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | **Default Google model.** `google` prefers Gemini CLI when installed |
| Gemini 3 Flash | `gemini-3-flash-preview` | Cheap. `-preview` required |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | No text-only 3.1 Flash yet |
| GPT-5.3 Instant | `gpt-5.3-chat-latest` | Reasoning max: **medium only**. Auto-defaults |
| GPT-5.4 | `gpt-5.4` | **Default OpenAI model.** `openai` prefers Codex CLI when installed. API fallback defaults reasoning to `high`; `xhigh` is also supported. |
| GPT-5.2 (legacy) | `gpt-5.2` | Legacy OpenAI default. |
| GPT-5-Codex | `gpt-5-codex` | No `minimal` reasoning-effort |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Hyphens, not dots |
| Grok 4.20 Reasoning | `grok-4.20-0309-reasoning` | Use `-p xai`. **Not in `_RECOMMENDED_MODELS`** — pass full name explicitly. |
| Grok 4.20 Non-Reasoning | `grok-4.20-0309-non-reasoning` | Latency tier, same backbone/price |
| Grok 4.20 Multi-Agent | `grok-4.20-multi-agent-0309` | `reasoning.effort` controls **agent count** (low/med→4, high/xhigh→16), not depth |
| Grok 4 (default) | `grok-4` | llmx's default xAI model — **superseded** by 4.20 family as of 2026-03-10 |
| Grok 4.1 Fast (cheap tier) | `grok-4-1-fast-reasoning` | xAI fast/cheap tier, still current |

**Model name format (v0.6.0+):** No provider prefixes needed. Use `gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`. Old LiteLLM-style prefixed names (`gemini/`, `openai/`) still accepted with deprecation warning. Will be removed in a future version.

**Model name suggestions:** If you typo a model name, llmx suggests the closest match: `"gemini-3.1-pro not found; did you mean gemini-3.1-pro-preview?"`

**404 traps:** `gemini-3-flash` (missing `-preview`), `gemini-flash-3` (wrong order), `gpt-5.3` (needs `-chat-latest` suffix).

## Token Limits

| Model | Max Input | Max Output | Notes |
|-------|----------|-----------|-------|
| GPT-5.4 | 1,050,000 | 128,000 | |
| GPT-5.2 | 272,000 | 128,000 | |
| GPT-5.3 Chat | 128,000 | 16,384 | Smallest output cap — watch for truncation |
| o4-mini | 200,000 | 100,000 | |
| Gemini 3.1 Pro | 1,048,576 | 65,536 | Server default is 8K — always pass `--max-tokens 65536` |
| Gemini 3 Flash | 1,048,576 | 65,535 | |
| Grok 4.20 Reasoning | 2,000,000 | 128,000 | **>200K input → 20× price tier** ($40/$120 per M). Chunk before crossing. |

## Reasoning Effort Values

| Model | Valid values | Default |
|-------|------------|---------|
| GPT-5.3 Instant | **medium only** | medium (auto) |
| GPT-5.4 | none, minimal, low, medium, high, xhigh | high |
| GPT-5.2 | minimal, low, medium, high | high |
| GPT-5-Codex | low, medium, high | high |
| Gemini 3 Flash | low, medium, high | high (server-side, via `thinking_config`) |
| Gemini 3.x (Pro/Flash) | low, medium, high | high (server-side, via `thinking_config`) |
| Grok 4.20 Reasoning | **NONE — passing `reasoning_effort` errors** | auto (model reasons internally) |
| Grok 4.20 Multi-Agent | low, medium, high, xhigh — **selects agent count, not depth** (low/med→4 agents, high/xhigh→16) | -- |
| Grok 4.20 Non-Reasoning | n/a (no thinking) | -- |

Temperature locked to 1.0 for GPT-5 and Gemini 3.x thinking models.

**Google API note:** Google uses `thinking_config` with `thinking_level` (not `reasoning_effort`) under the hood. llmx translates `--reasoning-effort` to the correct parameter per provider — you don't need to know this unless debugging raw API calls.

**OpenRouter streaming guard (v0.6.0+):** OpenRouter occasionally sends empty `choices` arrays in streaming chunks. llmx now guards against this — if you see `IndexError` on `choices[0]` in older versions, upgrade.

## Judge Names ≠ Model Names

| Context | Name |
|---------|------|
| llmx CLI | `gemini-3.1-pro-preview` |
| tournament MCP judges | `gemini25-pro` |
