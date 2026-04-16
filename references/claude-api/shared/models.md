# Claude Model Catalog

**Only use exact model IDs listed in this file.** Never guess or construct model IDs — incorrect IDs will cause API errors. For model IDs not listed here (older or retired versions), WebFetch the Models Overview URL in `shared/live-sources.md`.

## Current Models

| Friendly Name     | Model ID            | Context        | Max Output |
|-------------------|---------------------|----------------|------------|
| Claude Opus 4.7   | `claude-opus-4-7`   | 1M             | 128K       |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 200K (1M beta) | 64K        |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K           | 64K        |

### Model Descriptions

- **Claude Opus 4.7** — Most intelligent model for agents, coding, and long-horizon knowledge work. Adaptive thinking (off by default — set `thinking: {type: "adaptive"}` explicitly), effort levels `low | medium | high | xhigh | max` (`xhigh` recommended for coding/agentic). 1M native context at standard pricing (no beta header). 128K max output tokens — streaming required for large outputs. High-resolution image support up to 2576px / 3.75 MP. Task budgets available in beta (`task-budgets-2026-03-13`).
- **Claude Sonnet 4.6** — Best combination of speed and intelligence. Adaptive thinking. 1M context available via `context-1m-2025-08-07` beta header. 64K max output tokens.
- **Claude Haiku 4.5** — Fastest and most cost-effective model for simple tasks.

## Resolving User Requests

| User says...               | Use this model ID    |
|----------------------------|----------------------|
| "opus", "most powerful"    | `claude-opus-4-7`    |
| "sonnet", "balanced"       | `claude-sonnet-4-6`  |
| "haiku", "fast", "cheap"   | `claude-haiku-4-5`   |

For any other model request (older Opus, Sonnet, Haiku, or retired model), WebFetch the Models Overview URL from `shared/live-sources.md` to confirm the model exists and its current ID.
