# Claude Sonnet 5.5 — cost tier

> Replaced Sonnet 5 on 2026-11-10 (this file was `claude-sonnet-5.md`; git history keeps the Sonnet 5 guidance and its system-card digest stays at [sonnet-5-system-card.md](../sonnet-5-system-card.md)). Sonnet 5.5 was released 2026-09-28; this guide missed it for six weeks because no release check covered Sonnet/Haiku launches (CHANGELOG 2026-11-10).

**OPEN QUESTION (operator call, carried from Sonnet 5):** the 2026-06-20 verdict "architecture / design / high-reasoning critique → never Sonnet" was reached on Sonnet 4.6. Whether Sonnet 5.5 changes it has not been evaluated; the verdict stands until the operator revisits it.

## Specs

`claude-sonnet-5-5`, released 2026-09-28. $2/$10 per MTok (same as Sonnet 5), cache read $0.10 (5% of input; Sonnet 5 paid 10%), 5m write $2.50, 1h write $4. 1M context, 128K output (300K on the Batch API with `output-300k-2026-03-24`). Adaptive thinking on by default, API default effort `high`; it cannot be disabled, but `thinking: {type: "between_tools"}` turns off up-front thinking at `high` or below. `temperature`/`top_p`/`top_k` return 400. Minimum cacheable prompt 512 tokens. [Overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5).

**Transport (verified 2026-11-10, Claude Code 2.1.321):** `claude -p --model claude-sonnet-5-5` and the `sonnet` alias both report `modelUsage` = `claude-sonnet-5-5`. So every `model: sonnet` agent (`session-analyst`, `design-review`, `supervision-audit`) has served Sonnet 5.5 since the alias moved. llmx registers it on the subscription allowlist as of 2026-11-10.

## Role

**Use for:** cost-sensitive coding and agentic work with a mechanical gate (tests, typecheck), mechanical no-gate dispatch, and work dominated by untrusted tool output. The Fable 5.2 card's adaptive-attacker test measured attack success at 3.01% without probes and 2.63% with them on Sonnet 5.5, against Opus 5.5's 54.61% / 11.13% (§5.2.2; vendor-run). That makes it the injection-robust tier above Haiku 5.5.

The dispatch-tier evidence (Sonnet 4.6 changed the measurement procedure under gate pressure) predates both Sonnet 5 and 5.5. Keep architecture and partial-verifier work off this tier until it is re-measured.

Prompting: same XML-tag, no-prefill and no-sampling-parameter rules as the other current Claude models (PROMPTING_CLAUDE.md). Sweep effort on your own verifier; do not carry over Sonnet 5 settings.
