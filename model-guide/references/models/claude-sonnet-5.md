# Claude Sonnet 5 — cost tier

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L25, L253-266.

**OPEN QUESTION (2026-06-30, not yet resolved — operator call):** the "Architecture / design / high-reasoning critique → NEVER Sonnet" verdict below was reached against Sonnet 4.6 on 2026-06-20. Sonnet 5's system card shows large agentic/coding gains and prompt-injection robustness tying or beating Opus 4.8 in several places, but also the *worst* prefill/system-prompt-susceptibility numbers of the compared models and measurably more turns/tokens per task (system-card digest: `references/sonnet-5-system-card.md`). Whether this changes the "NEVER Sonnet" verdict for architecture/critique work is a live question, not re-litigated here — the verdict stands until the operator revisits it.

## Claude Sonnet 5 - "The Cost Tier" (added 2026-06-30)

**Use for:** cost-sensitive coding and agentic work with a mechanical gate (tests, typecheck), mechanical no-gate dispatch (rename sweeps, boilerplate), and work dominated by untrusted tool output or prompt injection. The Sonnet 5 system-card comparison and the unresolved architecture-routing question above remain model-specific evidence. Historical Agent-tool substitutions are recorded in Verified Transport; do not identify a served model from its writing style or self-report alone.

**Operational specs:** `claude-sonnet-5`, 1M context, 128K max output, **$3/M input and $15/M output** ($2/$10 introductory through 2026-08-31, vs Opus 5's $5/$25). Adaptive thinking on by default (unlike Sonnet 4.6, which ran thinking-off by default — omitting `thinking` now runs adaptive). First Sonnet-tier model with `xhigh` effort. New tokenizer vs Sonnet 4.6 (~30% more tokens for the same text — partially offsets the lower $/token). **Not yet on the subscription allowlist** (`lite_allowed_models` in `~/.claude/cache/llmx-routing.json` has no Sonnet entry, 4.6 or 5) — `llmx chat --subscription -m claude-sonnet-5` will not route until that allowlist is updated (llmx's own config, not this skill).

**System-card routing line** (digest: [references/sonnet-5-system-card.md](../sonnet-5-system-card.md)):
strongest measured prompt-injection robustness (ties/beats Opus 5); beats Sonnet 4.6 on nearly
every coding/agentic benchmark; watch-items — worst-of-cohort prefill/system-prompt susceptibility,
disclosed training-health issue (highest closed-book abstention of compared models), ~6%
evaluation-awareness, and more turns/tokens per task than Opus 4.8 (cheaper $/token ≠ cheaper
$/task on long loops — measure on your own workload).

**Prompting and API rules:** same XML-tag, no-prefill, no-non-default-sampling-param rules as Opus 5 (see `references/PROMPTING_CLAUDE.md` — written for Claude generally, applies here). Effort: default `high`; use `xhigh` for the hardest coding/agentic work in this tier (first Sonnet model to support it); `low`/`medium` for routine/mechanical dispatch per Dispatch Economics above.
