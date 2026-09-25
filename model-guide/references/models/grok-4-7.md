# Grok 4.7 — Cursor pool, Grok Build CLI, xAI API

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L324-396.

> Grok ≤4.6 ids are retired 2026-09-25, Pareto-frontier prune. The 4.6 and 4.5 history blocks, the AA snapshot, the 4.5 operational specs and every "4.6 still admitted" note below are historical.

## Grok 4.7 — Cursor pool, Grok Build CLI, xAI API

**Grok 4.7 (released 2026-09-21) is the current Grok.** [Launch page](https://x.ai/news/grok-4-7): same starting price and speed as 4.6 ($2 / $6 per million input / output tokens), plus a fast tier at twice the speed and twice the price. API id `grok-4.7`. The launch page says it is in Cursor, Grok Build, and the Grok API. The post does not restate context length; 4.6's 500k window is the working assumption until docs.x.ai is re-read.

**Verified live 2026-09-23** with `cursor-agent` signed in and `grok` updated to 1.0.41. `cursor-agent models` lists 4.7 as `grok-4.7-{low,medium,high,xhigh}[-fast]` — **no `cursor-` prefix**; the 2026-09-22 guess `cursor-grok-4.7-*` does not exist and is corrected throughout this guide. `grok models` (Grok Build CLI, 1.0.13 → 1.0.41) now lists `grok-4.7` (default) and `grok-4.7-build-fast` alongside `grok-4.6`/`grok-4.5`. Live smoke: `llmx chat --subscription -m grok-4.7` resolved to Cursor `grok-4.7-high` and replied; `grok -p -m grok-4.7` replied; the invented `grok-4.7-max` was refused. Critique pins `grok-4.7-high`.

**Vendor scores (launch page, xHigh vs peers — not an independent AA paste):**

| Benchmark | Grok 4.7 xHigh | Grok 4.6 High | GPT-5.6 Sol Max | Fable 5.1 Max |
|---|---:|---:|---:|---:|
| CursorBench 4.0 | 46.3% | 40.4% | 41.7% | 51.8% |
| DeepSWE v1.1 | 71.0% (high effort) | 65.2% | 72.7% | 70.0% |
| EEBench | 64.0% | 53.0% | 39.4% | 56.4% |
| AA Briefcase v1.1 | 1657 | 1546 | 1487 | 1678 |
| Terminal-Bench 4.0 | 38.0% | 20.3% | 37.3% | 57.9% |
| Harvey Legal Agent | 19.6% | 15.8% | 2.5% | 6.7% |
| HealthBench Professional | 56.7% | 48.5% | 60.5% | 62.1% |

Launch-page token prices in that same table: Grok $2/$6, Sol $4/$20, Fable $10/$50. Do not overwrite the Sol/Fable price table from this comparison. CursorBench stays contaminated-until-proven-otherwise. Calibration is not remeasured; the 4.5 AA figures below are still the last independent ones.

**Grok 4.6 history.** Released 2026-08-12; Cursor pool on 2026-09-05 (`cursor-grok-4.6-{low,medium,high,xhigh}[-fast]`). Those slugs stay admitted. [historical: retired 2026-09-25, Pareto-frontier prune] The 2026-09-05 Grok Build smoke served `grok-4.6-build`.

**Grok 4.5 history.** SpaceXAI frontier model (2026-07-08), jointly trained with Cursor. Independent AA
measurement put it in the **frontier pack on capability** with a **cost/speed edge** and
**mid-pack calibration**. Cursor's exact Grok slugs are live again as of 2026-07-14; use this
as an opt-in read-only repo-review axis, not a replacement for Opus/GPT judgment or primary evidence.

**AA snapshot (high effort, operator paste 2026-07-09 — treat as screen, not verifier):**

| Metric | Grok 4.5 | vs peers (same paste) | Routing read |
|---|---:|---|---|
| Intelligence Index | **54** | Fable 60 · Opus 56 · GPT ~55 · GLM 51 | Frontier-capable; not #1 |
| Coding Index | **72.4** | Fable 76.5 · GPT 74.9 · Opus 74.3 | Near Opus/GPT for coding |
| Terminal-Bench v2.1 | **82%** | Fable/Opus 85 · GPT 84 | Parity band |
| AutomationBench-AA | **51%** | Fable/Opus 49 · GPT 42 | **Lead** — tool/SaaS workflows |
| τ³-Banking | **33%** | GPT 31 · Opus 28 | **Lead** — agentic tool use |
| AA-Briefcase Elo | **1328** | Fable 1583 · Opus 1354 · GPT 1158 | Strong knowledge-work agent |
| CritPt | **15%** | GPT-Pro 31 · Fable 29 · Opus 21 | **Weak** — hard physics |
| AA-Omniscience accuracy | **52%** | Fable 61 · GPT 57 · Opus 47 | Solid recall |
| AA-Omniscience non-hallucination | **~46%** | GLM 72 · Opus 64 · Fable 45 · GPT 14 | Mid-pack — not a fact source |
| Cost / Intelligence task | **~$0.31** | GPT $0.86 · Opus ~$1.8 · Fable $2.75 | **Use more when $ matters** |
| Output speed | **~88 tok/s** | Flash 167 · Fable 70 · GPT 68 | Faster than Fable/GPT |

**Admission gate (enforced on every critique dispatch):** the live registry must expose exact slug
`grok-4.7-high`, and an unrevealed exact repo-HEAD canary must prove read-only workspace
access. Any failure blocks the axis before reviewer dispatch.

**Use less / never alone:**
1. **Unsourced facts / "should we even do this?"** — ~46% non-hallucination; tools + Opus/GLM for epistemic guardrails.
2. **Hard quantitative / CritPt physics** — 15%; use GPT-6 Astra pro mode.
3. **Sole architecture judge** — still Opus `max` + GPT cross-lab; Grok is the *repo* axis, not the taste axis.
4. **Contexts >500k** — API window is 500k; Opus/GPT are 1M-class.
5. **CursorBench scores** — Cursor blog: training contamination; excluded from their table.

**Operational specs (API, 4.5 era — superseded by the 4.6 line above):** `grok-4.5`, **500k context**, $2/$6 per MTok, reasoning `low`/`medium`/`high` (default high). Fast Cursor variant $4/$18.

**Surfaces:**
| Surface | How | Status (verified live 2026-09-23) |
|---|---|---|
| Critique `grok` axis | `model-review.py --axes standard,grok` | Pin is `grok-4.7-high`. Preflight passes: `cursor-agent models` lists that exact id. 4.6 slug still admitted. [historical: retired 2026-09-25, Pareto-frontier prune] |
| Cursor session / `cursor-agent` | `--model grok-4.7-high --mode ask --workspace <repo>` | `cursor-agent models` confirms `grok-4.7-{low,medium,high,xhigh}[-fast]` (no prefix) and still lists `cursor-grok-4.6-xhigh`. |
| Grok Build headless | `grok -p "<prompt>" --output-format json -m grok-4.7 --reasoning-effort high --no-plan` | **Verified live**: `grok` updated to 1.0.41; `-m grok-4.7` replied. 2026-09-05 smoke on 1.0.13 served `grok-4.6-build`; served model on 4.7 not yet re-captured. |
| llmx Cursor pool | `llmx chat --subscription -m grok-4.7-high` (bare `-m grok-4.7` also resolves here) | **Verified live** — replied. |
| llmx Grok Build | `llmx chat -p grok -m grok-4.7 -e high` | Default when `-m` is omitted. Explicit `-m grok-4.6` still allowed. [historical: retired 2026-09-25, Pareto-frontier prune] |
| llmx xAI API | `llmx chat -p xai -m grok-4.7 -e high` | Model id added. Key status unverified since the 2026-07-09 403. |

**Footgun (updated 2026-09-23):** exact Cursor CLI slugs for 4.7 carry **no**
`cursor-` prefix — `grok-4.7-{low,medium,high,xhigh}[-fast]` — while 4.6 keeps
`cursor-grok-4.6-` and places `-fast` last. Bare `grok-4.7` (no effort suffix) is
the xAI / Grok Build id, not a Cursor CLI slug. Current llmx refuses any
`auth=subscription` plan that resolves to `xai-api`.

See `agent-infra/decisions/2026-07-09-grok-4.5-transport.md`.
