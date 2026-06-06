# Model Guide Changelog

## 2026-06-06 - Narrow model-guide to Opus 4.8 and GPT-5.5

Removed the broad active model catalog from `model-guide`.

### Removed from active routing

- Claude Sonnet fallback routing.
- GPT-5.4 and GPT-5.3 Instant active sections.
- Gemini 3.x active routing and `PROMPTING_GEMINI.md`.
- Grok 4.20 active routing.
- Broad cost-optimization tables that encouraged model-shopping instead of a clear frontier default.

Historical details remain available in git history. This skill now answers only the current high-value question: Opus 4.8, GPT-5.5, or GPT-5.5 Pro?

### Added / retained

- Opus 4.8 system-card insights: honesty/self-verification, reduced destructive actions, grader-speculation watch, prompt-injection caveat, high-effort default, mid-conversation system messages, dynamic workflows.
- GPT-5.5 system-card insights: destructive-action metrics, factuality caveat, low-severity coding-agent misalignment patterns, low CoT controllability, impossible-coding-task lying rate, High bio/chem and High-below-Critical cyber classification.
- GPT-5.5 Pro positioning: same underlying model plus parallel test-time compute, $30/$180 pricing, use only for verified high-stakes derivation.
- Current benchmark table and pricing table limited to Opus 4.8, GPT-5.5, and GPT-5.5 Pro.

### Sources checked

- Anthropic system-card registry and Opus 4.8 launch/API pages.
- Local vendored Opus 4.8 system card.
- OpenAI GPT-5.5 announcement, system card, API pricing, and model comparison docs.
