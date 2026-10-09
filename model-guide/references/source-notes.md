# Source notes

> Moved from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Retired-model content pruned 2026-09-25 (git history keeps it). Source lines: L421-435.

## Source Notes

Primary sources consulted for this update:
- Anthropic: `https://www.anthropic.com/news/claude-opus-5`
- Anthropic Opus 5.5 (read 2026-09-22): `https://www.anthropic.com/claude-opus-5-5`; system card `https://anthropic.com/claude-opus-5-5-system-card` (230-page PDF)
- OpenAI GPT-6 Sol/Luna (read 2026-09-25): `https://openai.com/index/introducing-gpt-6-sol-and-luna/`, model pages on developers.openai.com
- OpenAI GPT-6.1 Sol model page (read 2026-10-09): `https://developers.openai.com/api/docs/models/gpt-6.1-sol` — $2/$10, cached $0.10, 1.05M ctx, 128K out, effort low…max (no none/minimal), Chat Completions without tools; Codex CLI ≥0.162 for subscription
- Independent benchmarks: artificialanalysis.ai (2026-06-11) with instrument-validity reads of AA-Omniscience/IFBench/GDPval/τ² — `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`
- Calibration + reasoning-budget anecdote: Oliver Shrimpton, "Bigger models are not the way" (2026-06-18) — AA-Omniscience hallucination rates for GLM-5.2/DeepSeek V4 Pro; impossible-asyncio n=1 probe on OpenRouter
- Agent-tool routing-bug finding: arc-agi session 41f9b649, 2026-07-12 (fable ×5/5 self-reports; opus ×1 fresh probe, agent `a8afa4bad056a6f61`)
