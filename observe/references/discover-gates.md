<!-- Reference file for observe skill (discover mode). Loaded on demand. -->
# `discover` failure-mode gates

Mandatory. A phase that skips its gate is a known-failure repeat.

| # | Failure | Prevention gate |
|---|---------|-----------------|
| F1 | researching already-built features | **inventory gate**: grep `scripts/*.py` for concept keywords before ANY research |
| F2 | prompt-driven file output | **tool gate**: use the shared file-output contract; never rely on prompt text to create or overwrite |
| F3 | model timeout on large context | **context gate**: <15KB for the Gemini lane, <50KB for the GPT lane |
| F4 | duplicate frontier candidates re-entering | **idempotency gate**: maintain an existing-ID ban list |
| F5 | tool-call schema mismatch | **schema gate**: validate payload shape before dispatch |
| F6 | fixed survivor quota padding weak ideas | **calibration gate**: default 0-2 survivors; **0 is healthy** |
| F7 | concept duplicates under new phrasing | **semantic dedup gate**: check concept overlap, not just IDs |
| F8 | long-memo append corruption | **append-at-tail gate**: inspect the file tail before every append |

Phases and budgets: 1 inventory ~10% (F1,F7) · 2 brainstorm ~15% (F1,F4) · 3 research ~25% (F1-F6) ·
4 plan ~15% · 5 model review ~15% (F3) · 6 implement ~20% — one reference file each,
`references/phase-N-*.md`. Up to 3 Claude agents + 2 GPT dispatches in parallel, one idea per agent.
**Every object must have a caller — dead code with a plan does not pass.** Stopping after phase 4 is
legitimate.

Phase files, in order: `references/phase-1-inventory.md` · `references/phase-2-brainstorm.md` ·
`references/phase-3-research.md` · `references/phase-4-plan.md` · `references/phase-5-review.md` ·
`references/phase-6-implement.md`. Cross-cutting concerns that span several of them (budget
discipline, dispatch hygiene, artifact handling) are in `references/operational-discipline.md`.
