---
name: model-guide
description: "Choose a model and effort by principle: the cheapest frontier model that passes the task's verifier, cross-lab review for consequential judgment, facts from tools. Pareto-frontier roster (Opus 5.5, GPT-6.1 Sol, GPT-6 Astra/Luna, Gemini 4 Argon, Fable 5.1, Grok 4.7, DeepSeek on LithosAI, opt-in lanes); per-model prompting in references. Transport flags: /llmx-guide."
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Choose a model and effort from the principles below, then read the model's reference file for prompting and watch-items. Transport mechanics belong to `/llmx-guide` and the live mirror `llmx info`.

## Principles (full wording and evidence: [principles.md](references/principles.md))

1. **Use the cheapest model and effort that passes the task's verifier.** The brief's verifier sets the tier, not how hard the task feels; a gate-less brief makes your review the gate ([Dispatch Economics](references/dispatch-economics.md)).
2. **Subscription: every tier is $0, so choose by quality and plan headroom. Metered: the cheapest tier that passes.** Claude runs on the subscription only; metered Anthropic API needs an explicit request.
3. **Route only to the Pareto frontier: retire dominated models and migrate their callers.** A dominated id left in an allowlist gets picked by accident.
4. **Effort is a per-model dial tuned against the verifier. Never switch to a weaker model as a fix.** Effort names do not carry across models (Opus 5.5 at `low` collapses on research). Prefer tools and in-loop checks over extra thinking ([trilemma](references/selection-trilemma.md)).
5. **Cross-model review for consequential judgment; a model grading its own output is not review.** Run a second diverse pass and check every fact a reviewer asserts ([review pattern](references/cross-model-review.md)).
6. **Facts come from tools, not model recall.** Without a source, pick for calibration (willingness to abstain) over rank or size; require an execution receipt for computed numbers.
7. **Probe the live transport and read back the served model before trusting config.** Aliases and dry-runs prove configuration only; a self-report is not proof ([transport](references/transport.md)).
8. **Vendor benchmarks are claims. Check `~/Projects/evals/DECISIONS.md` before any bake-off.** A fresh n=1 probe must not overturn a settled eval. Treat CursorBench as contaminated.
9. **Route classifier niches by exact id.** Opus 5.5 re-routes most cyber work to Opus 4.8 and declines dual-use biology: send that work to `claude-opus-5` by exact id.
10. **Work the principal verifies (taste, voice, conviction) stays with the operator.** Models draft and critique; a model judge does not make taste verifiable.

## Roster (Pareto frontier, 2026-10-26; why each is on the frontier: [roster.md](references/roster.md))

**Newest picks (operator 2026-10-26: "newest models always"):** `gpt-6.1-sol`, `gpt-6-astra`, `claude-opus-5-5`, `gemini-4-argon`. Pin an older id only when an eval or a classifier niche (principle 9) requires it.

| Model | Role | Transport |
|---|---|---|
| [claude-opus-5-5](references/models/claude-opus-5-5.md) | Default Claude: coding (`medium`), hard work (`xhigh`), architecture (`max`), research (`high`+) | Subscription: `opus` alias, Agent tool, `llmx --subscription` |
| [claude-fable-5-1](references/models/claude-fable-5-1.md) | Named-edge lane; the operator's interactive choice | Subscription (Max allowance), claude-cli |
| [claude-opus-5](references/models/claude-opus-5.md) | Cyber and dual-use biology work; lanes pinned to it | Subscription, exact id only |
| [claude-sonnet-5](references/models/claude-sonnet-5.md) | Cost tier: gated coding, no-gate mechanical work, injection-heavy input | Agent tool / `claude -p`; not on the llmx subscription allowlist |
| claude-haiku-4-5 | Cheapest Claude for mechanical no-gate work | Agent tool; llmx anthropic-direct |
| [gpt-6-astra](references/models/gpt-6-astra.md) | Default GPT: headless cheap lane at `low` (incl. the `/critique` premise scout and `/diff-review` scout), Codex implementation, cross-lab reviewer, quantitative work (pro mode) | codex-cli subscription (`llmx --subscription`, `codex exec`) |
| [gpt-6.1-sol](references/models/gpt-6.1-sol-luna.md) | Metered mid tier; fallback when Astra's plan limit binds | Codex subscription + API |
| [gpt-6-luna](references/models/gpt-6.1-sol-luna.md) | Metered bulk extraction and mechanical work | Codex subscription + API |
| [grok-4.7](references/models/grok-4-7.md) | Opt-in read-only repo critique axis; Grok Build headless | cursor-agent `grok-4.7-<effort>[-fast]`; `grok` CLI; xAI API unverified |
| [gemini-4-argon](references/models/gemini.md) | Default Gemini: critique Gemini axes (`arch`, `gaps`) since 2026-10-14 (operator), never the sole reviewer; weak agentic coder | Metered API (`GEMINI_API_KEY_METERED`) |
| DeepSeek V4.1 Flash on LithosAI | Metered bulk and opencode `lane` work where price or wall time beats quality; facts from tools (V4 Pro calibrated badly) | `llmx -p lithosai -m deepseek-flash` (base, $0.15/$0.60) / `deepseek-flash-fast` ($0.25/$1.00) / `deepseek-flash-ultra` ($0.35/$1.40, 429s under concurrency) |
| [GLM-5.2](references/models/glm-5-2.md) | Opt-in review cosigner and epistemic guardrail; not an extractor | OpenRouter/zai metered, `--axes …,glm` |
| [kimi-k3](references/models/kimi-k3.md) | Opt-in long-horizon coding probe | `llmx -p kimi` metered; Kimi Code CLI |

Older / pinned only: `gemini-3.8-flash` (still llmx's default for `-p google`, vision and batch: pass `-m gemini-4-argon`), `gemini-3.1-pro-preview`, `gemini-3.5/3.1-flash-lite` (priced, not routed). llmx refuses `-p deepinfra` (retired 2026-10-26).

Retired 2026-09-25 (operator: allowlists hold the Pareto frontier only): every model not in this table; git history keeps their old guidance. Retired 2026-10-07 (operator: "outdated"): composer-2.5 and composer-2.5-fast; successor gpt-6-astra at `low` effort, with gpt-6.1-sol at `high` when Astra's plan limit binds.

## Settled operator decisions

- Claude runs on the subscription only; the metered API requires an explicit request.
- Architecture, design and high-reasoning critique use Opus `max` plus GPT-6 Astra, never Sonnet (2026-06-20). **Open:** whether Sonnet 5 changes that verdict is the operator's call ([details](references/models/claude-sonnet-5.md)).
- Allowlists hold the Pareto frontier only (2026-09-25). llmx refuses retired ids with the successor named.
- Gemini is an ordinary metered provider (critique-only gate lifted 2026-10-14).
- DeepSeek runs on LithosAI only (2026-10-26); DeepInfra is retired.
- GLM-5.2 is an opt-in cosigner, not an extractor (2026-06-19).
- Moving the interactive setting off Fable 5.1 is the operator's call.
- `opus-low` is licensed for briefed, gated execution only; research and synthesis run at `medium` or higher.

## References

- Per-model specs, prompting and watch-items: [references/models/](references/models/). Prompting guides: [Claude](references/PROMPTING_CLAUDE.md), [GPT](references/PROMPTING_GPT.md).
- Choosing an executor tier (the "Dispatch Economics" section other skills cite): [dispatch-economics.md](references/dispatch-economics.md). Cosigner defaults: [cosigner-defaults.md](references/cosigner-defaults.md).
- Verified lanes and llmx facts: [transport.md](references/transport.md).
- Scores: [BENCHMARKS.md](references/BENCHMARKS.md). System-card digests: [Opus 5.5](references/opus-5-5-system-card.md), [Opus 5](references/opus-5-system-card.md), [Sonnet 5](references/sonnet-5-system-card.md).
- Checks after output: [validation-checklists.md](references/validation-checklists.md). Sources: [source-notes.md](references/source-notes.md). History: [CHANGELOG](references/CHANGELOG.md).

## When to Update This Skill

When a model is released or a system card is materially revised (full wording: end of [CHANGELOG.md](references/CHANGELOG.md)):
1. Read the model card; update `references/models/<slug>.md`, `references/BENCHMARKS.md` and the prompting guide.
2. Update the roster row here and in [roster.md](references/roster.md); register the id in llmx (`llmx info` must show it).
3. Prune dominated ids from llmx allowlists and the roster and migrate every caller; inventory first (`rg -c`, then page through all matches).
4. Update [transport.md](references/transport.md) when a lane starts or stops serving its claimed model; re-probe, don't assume.
5. Add a dated entry to [CHANGELOG.md](references/CHANGELOG.md). Change principles only when evidence changes.

To log a defect or point of friction: `~/Projects/skills/hooks/append-skill-memento.sh model-guide '<one-line issue>'`.

## Known Issues

For matching failures, read [incident history](references/known-issues.md). The memento helper appends there.
