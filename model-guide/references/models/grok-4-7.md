# Grok 4.7 — Cursor pool, Grok Build CLI, xAI API

> Moved from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Retired-model content pruned 2026-09-25 (git history keeps it). Source lines: L324-396.

## Grok 4.7 — Cursor pool, Grok Build CLI, xAI API

**Grok 4.7 (released 2026-09-21) is the current Grok.** [Launch page](https://x.ai/news/grok-4-7): same starting price and speed as 4.6 ($2 / $6 per million input / output tokens), plus a fast tier at twice the speed and twice the price. API id `grok-4.7`. The launch page says it is in Cursor, Grok Build, and the Grok API. The post does not restate context length; 500k (the prior Grok window) is the working assumption until docs.x.ai is re-read.

**Verified live 2026-09-23** with `cursor-agent` signed in and `grok` updated to 1.0.41. `cursor-agent models` lists 4.7 as `grok-4.7-{low,medium,high,xhigh}[-fast]` — **no `cursor-` prefix**; the 2026-09-22 guess `cursor-grok-4.7-*` does not exist and is corrected throughout this guide. `grok models` (Grok Build CLI, 1.0.13 → 1.0.41) now lists `grok-4.7` (default) and `grok-4.7-build-fast`. Live smoke: `llmx chat --subscription -m grok-4.7` resolved to Cursor `grok-4.7-high` and replied; `grok -p -m grok-4.7` replied; the invented `grok-4.7-max` was refused. Critique pins `grok-4.7-high`.

**Vendor scores (launch page, xHigh vs peers — not an independent AA paste):**

| Benchmark | Grok 4.7 xHigh | Fable 5.1 Max |
|---|---:|---:|
| CursorBench 4.0 | 46.3% | 51.8% |
| DeepSWE v1.1 | 71.0% (high effort) | 70.0% |
| EEBench | 64.0% | 56.4% |
| AA Briefcase v1.1 | 1657 | 1678 |
| Terminal-Bench 4.0 | 38.0% | 57.9% |
| Harvey Legal Agent | 19.6% | 6.7% |
| HealthBench Professional | 56.7% | 62.1% |

Launch-page token prices in that same table: Grok $2/$6, Fable $10/$50. CursorBench stays contaminated-until-proven-otherwise. Calibration has no independent 4.7 measurement yet.

**Admission gate (enforced on every critique dispatch):** the live registry must expose exact slug
`grok-4.7-high`, and an unrevealed exact repo-HEAD canary must prove read-only workspace
access. Any failure blocks the axis before reviewer dispatch.

**Use less / never alone:**
1. **Unsourced facts / "should we even do this?"** — no independent 4.7 calibration read; tools + Opus/GLM for epistemic guardrails.
2. **Hard quantitative / CritPt physics**; use GPT-6 Astra pro mode.
3. **Sole architecture judge** — still Opus `max` + GPT cross-lab; Grok is the *repo* axis, not the taste axis.
4. **Contexts >500k** — API window is 500k; Opus/GPT are 1M-class.
5. **CursorBench scores** — Cursor blog: training contamination; excluded from their table.


**Surfaces:**
| Surface | How | Status (verified live 2026-09-23) |
|---|---|---|
| Critique `grok` axis | `model-review.py --axes standard,grok` | Pin is `grok-4.7-high`. Preflight passes: `cursor-agent models` lists that exact id. |
| Cursor session / `cursor-agent` | `--model grok-4.7-high --mode ask --workspace <repo>` | `cursor-agent models` confirms `grok-4.7-{low,medium,high,xhigh}[-fast]` (no prefix). |
| Grok Build headless | `grok -p "<prompt>" --output-format json -m grok-4.7 --reasoning-effort high --no-plan` | **Verified live**: `grok` updated to 1.0.41; `-m grok-4.7` replied. Served model on 4.7 not yet re-captured. |
| llmx Cursor pool | `llmx chat --subscription -m grok-4.7-high` (bare `-m grok-4.7` also resolves here) | **Verified live** — replied. |
| llmx Grok Build | `llmx chat -p grok -m grok-4.7 -e high` | Default when `-m` is omitted. |
| llmx xAI API | `llmx chat -p xai -m grok-4.7 -e high` | Model id added. Key status unverified since the 2026-07-09 403. |

**Footgun (updated 2026-09-23):** exact Cursor CLI slugs for 4.7 carry **no**
`cursor-` prefix — `grok-4.7-{low,medium,high,xhigh}[-fast]`. Bare `grok-4.7` (no effort suffix) is
the xAI / Grok Build id, not a Cursor CLI slug. Current llmx refuses any
`auth=subscription` plan that resolves to `xai-api`.

See `agent-infra/decisions/2026-07-09-grok-4.5-transport.md`.
