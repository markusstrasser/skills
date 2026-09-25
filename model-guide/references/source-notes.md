# Source notes

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L421-435.

## Source Notes

Primary sources consulted for this update:
- Anthropic: `https://www.anthropic.com/news/claude-fable-5-mythos-5`
- Anthropic Fable 5 system card: `https://www.anthropic.com/claude-fable-5-mythos-5-system-card`
- Anthropic docs: `https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5`
- Anthropic Fable prompting guide: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Anthropic: `https://www.anthropic.com/news/claude-opus-5`
- Anthropic Opus 5.5 (read 2026-09-22): `https://www.anthropic.com/claude-opus-5-5`; system card `https://anthropic.com/claude-opus-5-5-system-card` (230-page PDF)
- OpenAI GPT-6 Sol/Luna (read 2026-09-25): `https://openai.com/index/introducing-gpt-6-sol-and-luna/`, model pages on developers.openai.com
- OpenAI GPT-5.6: `https://openai.com/index/gpt-5-6/`, pricing/models docs on developers.openai.com
- Cross-repo harness analysis: `agent-infra/research/2026-06-09-fable-5-mythos-5-harness-impact.md`
- Independent benchmarks: artificialanalysis.ai (2026-06-11) with instrument-validity reads of AA-Omniscience/IFBench/GDPval/τ² — `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`
- Calibration + reasoning-budget anecdote: Oliver Shrimpton, "Bigger models are not the way" (2026-06-18) — AA-Omniscience hallucination rates for GLM-5.2/DeepSeek V4 Pro; impossible-asyncio n=1 probe on OpenRouter
- Agent-tool routing-bug finding: arc-agi session 41f9b649, 2026-07-12 (fable ×5/5 self-reports; opus ×1 fresh probe, agent `a8afa4bad056a6f61`)
