# llmx cosigner / dispatch defaults

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L119-123, L125, L163.

## llmx Cosigner / Dispatch Defaults (judgment — transport in mirror)

- **Cosigner / critique / synthesis:** `gemini-3.8-flash` (GA 2026-09-02; intro $0.75/$3.75 through 2026-12-31). **Always in the 2G+2GPT mix — never the only reviewer.** Probe flags invention on clean packets; orchestrator dispositions via `--extract --verify`.
- **Cheap classification / mechanical audits:** `gpt-6-astra` at `low` via codex-cli subscription ($0). Luna does not beat Astra-low on quality (AA Astra-low 57 vs Luna-max 43); for metered API bulk use `-m gpt-6-luna` (GPT-6 Luna not yet measured on AA). Gemini is critique-only since 2026-07-14.
- **GPT-6 Astra default effort:** preserve the requested effort; `none`/`minimal` map to `low`. Suite supports `max`. Pass `-e high`/`xhigh`/`max` for depth; reasoning bills as output.

- **Grok 4.7 is the current Grok (released 2026-09-21).** Cursor CLI grammar for 4.7 is `grok-4.7-{low,medium,high,xhigh}[-fast]` — **no `cursor-` prefix**, verified live 2026-09-23; 4.6 keeps `cursor-grok-4.6-*` and stays admitted. [historical: Grok ≤4.6 retired 2026-09-25, Pareto-frontier prune] The opt-in critique `grok` axis pins `grok-4.7-high` and fails closed on registry or unrevealed repo-canary drift. Bare `grok-4.7` (no effort suffix) is the xAI / Grok Build id, not a Cursor slug.

- GLM-5.2 opt-in cosigner bullet: [models/glm-5-2.md](models/glm-5-2.md). Gemini registration, Flash-Lite and 3.1-pro bullets: [models/gemini.md](models/gemini.md). `llmx vision` bullet: [transport.md](transport.md).
- **Cosigner calibration caveat (AA-Omniscience, 2026-06-11):** both cosigner defaults are bottom-quartile abstainers — non-hallucination 39% (`gemini-3.5-flash` [historical: retired 2026-09-25, Pareto-frontier prune; cosigner is now `gemini-3.8-flash`, not re-measured]), prior GPT class 14% (re-measure Luna/Sol TBD), despite an abstention prompt. Critique output = adversarial pressure on reasoning, never a fact source; **for fact-heavy review where calibration matters, verify novel specifics at primary and lean on a frontier model (Opus/GPT), not a cheap cosigner.** Instruments: agent-infra `research/2026-06-11-aa-benchmark-instrument-validity.md`.
