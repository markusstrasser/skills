# GPT-6 Astra — default GPT

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L13-19.

## GPT-6 Astra

For Astra prompting or migration, read [current GPT guidance](../PROMPTING_GPT.md), verified against the official guide on 2026-09-05. Apply persistent authorized execution, explicit skill precedence, concise prose, useful bounded delegation and proportionate verification. Preserve effective effort, including `max`; `none`/`minimal` migrate to `low`.

The operator's Codex configuration selects Astra. Check the actual transport and its applied model/effort before a model-sensitive dispatch. Existing lower-cost task profiles and evaluation pins keep their roles; GPT-6 Luna is the metered cheap extract/mechanical lane. Dated judgments below apply to their named models and harnesses, not automatically to Astra.

**Operational specs:** `gpt-6-astra` (alias `gpt-6`). API $10/$50 per MTok (2×/1.5× above 272K input); Fast mode 2× Standard. 1.05M context, 128K max output. Effort `low|medium|high|xhigh|max`; `none`/`minimal` map to `low`. Subscription via `llmx chat --subscription -m gpt-6-astra` or `codex exec` (omit `-m`) is $0 against the ChatGPT plan. Source: developers.openai.com/api/docs/models/gpt-6-astra (2026-09-05).
