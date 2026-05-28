# Claude Model Catalog

**Only use exact model IDs listed in this file.** Never guess or construct model IDs — incorrect IDs will cause API errors. For model IDs not listed here (older or retired versions), WebFetch the Models Overview URL in `shared/live-sources.md`.

## Current Models

| Friendly Name     | Model ID            | Context        | Max Output |
|-------------------|---------------------|----------------|------------|
| Claude Opus 4.8   | `claude-opus-4-8`   | 1M             | 128K       |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 200K (1M beta) | 64K        |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K           | 64K        |

### Model Descriptions

- **Claude Opus 4.8** — Most intelligent model for agents, coding, and long-horizon knowledge work (released 2026-05-28, replaces 4.7; pricing unchanged $5/$25). Materially more honest than 4.7 — flags uncertainty more readily and is ~4× less likely to let flaws in its own code pass unremarked. Effort levels `low | medium | high | xhigh | max`; **defaults to `high`** (`xhigh` recommended for coding/agentic, `max` for the hardest tasks). Adaptive thinking (off by default — set `thinking: {type: "adaptive"}` explicitly). 1M native context at standard pricing (no beta header). 128K max output tokens — streaming required for large outputs. High-resolution image support up to 2576px / 3.75 MP. The Messages API now accepts `system` entries inside the `messages` array — update instructions mid-run without breaking the prompt cache. Fast mode: 2.5× output speed at $10/$50 (3× cheaper than fast mode for prior models). Task budgets available in beta (`task-budgets-2026-03-13`).
- **Claude Sonnet 4.6** — Best combination of speed and intelligence. Adaptive thinking. 1M context available via `context-1m-2025-08-07` beta header. 64K max output tokens.
- **Claude Haiku 4.5** — Fastest and most cost-effective model for simple tasks.

## Resolving User Requests

| User says...               | Use this model ID    |
|----------------------------|----------------------|
| "opus", "most powerful"    | `claude-opus-4-8`    |
| "sonnet", "balanced"       | `claude-sonnet-4-6`  |
| "haiku", "fast", "cheap"   | `claude-haiku-4-5`   |

For any other model request (older Opus, Sonnet, Haiku, or retired model), WebFetch the Models Overview URL from `shared/live-sources.md` to confirm the model exists and its current ID.
