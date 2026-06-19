<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Dispatch Mechanics

## Default economics: presets + subparts

**Presets** (see `model-review.py` PRESETS):

| Preset | Geometry | When |
|--------|----------|------|
| `standard` | 2×2 / 4 lenses (CLI default until ROUTING_VERDICT) | Legacy / closeout |
| `cross2` / `lens2` | diagonal S_G + M_P | Routine design (triage recommends; not CLI default yet) |
| `cross4` / `lens4` | full 2×2 grid | Governance, multi-repo, INCONCLUSIVE≥3, **contradictory anchors** |

1. **Split** the review into 2–4 subparts (phases, directories, risk tiers).
2. **Run `review_gate.py triage`** → `dispatch.json` includes `preset`, `dispatch_policy`
   (scout/scope/budget), and `preset_reasons`.
3. **Per subpart**, dispatch from triage:
   ```bash
   model-review.py --dispatch-manifest .model-review/dispatch.json \
     --context packet.md --topic "..." "Review"
   ```
   CLI flags override manifest fields when explicitly passed.
   - Optional: `--cross-talk` on cross2/cross4 — structure lenses first, inject
     `structural-assumptions.json` into mechanism passes (sequential; default parallel).
4. **Merge** findings across subparts.

`arch` / `correctness` prompts include folded gaps/contracts checklists. Separate `gaps`/`contracts` axes remain for `standard`/`cross4` until ablation promotes `cross2`.

Smaller packets → fewer tokens → lower cost. Split lenses → more findings than one mega-pass.

**Deterministic gate (run before dispatch):** `review_gate.py triage` reads the packet
manifest + git diff, writes `.model-review/dispatch.json` (layers, blockers, token budget).

**VOI premise scout (default on):** runs unless `--no-scout` or `--context-scope packet`
(single-file / clear req-res / context-free). `--irreversible` gates on executed
`conviction=low`; skip ≠ low. See `decisions/2026-06-15-voi-sequenced-review.md`.

**Orchestrator wall-clock budget (opt-in):** `--budget-seconds SEC` — no limit by default.
Applies to **parallel axis dispatch + extract only**; premise scout has a fixed timeout
and does not consume this cap (scout timeout previously cascaded into all axes skipped
as `budget_exhausted`). When set: skip axis/extract if `remaining < profile.timeout`
(full job or nothing; never truncate). Skipped axes → `budget_exhausted` or
`budget_insufficient_for_profile` (cap smaller than profile timeout at start);
`execution-receipt.json` records `overall: partial|incomplete_all_skipped` (dispatch exits 2).

`dispatch.json` includes `schema_version: dispatch.v1`. Triage exits **1** on blockers.

```bash
model-review.py --budget-seconds 480 --context plan.md --topic "gateway" --axes standard,formal "Review"
```

After review: `review_gate.py rank` → `orchestrator-top.json` + `anchor-contradictions.json`
+ `escalation-recommendation.json` (when contradictory pairs ≥1); `outcome_link.py` uses
`linked_anchor` (evidence) not file-touch alone; `integration_audit.py` before commit.

**Escalation ontology:** `contradictory_anchors` = cross-family opposite stance on overlapping topic
(same file + shared entity terms). **Non-overlap** (different issues, same file) does **not** escalate.

Add `--axes standard,formal` only on subparts with math/Bayes/proofs/invariants (GPT **high**).
Add `composer` or `claude` as third lineage on high-stakes diffs — not instead of the 4-axis core.

## Shared Dispatch Contract

The review script owns transport, context packing, output files, extraction, and
verification. Prefer the script over ad hoc model calls:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "What's wrong with this [thing being reviewed]"
```

Use `--verify` when the review is a plan-close packet or when you want the script
to check file/symbol references after extraction. After triage, manifest carries
`extract`/`verify` — auto-loaded from `.model-review/dispatch.json` when present:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo "$(pwd)" --packet .model-review/plan-close-context.md --mode close

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context .model-review/plan-close-context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  "Review this plan closeout"
```

No `--budget-seconds` unless the session is time-boxed (no wall-clock limit by default).

Other useful forms:

```bash
# Deep review with per-axis overrides
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context-files docs/plan.md scripts/finding_ir.py:86-110 \
  --topic "$TOPIC" \
  --axes arch,formal,domain,mechanical \
  --questions questions.json \
  --extract \
  "Review this plan"
```

## Contract Boundaries

Transport/model choices live in `shared/llm_dispatch.PROFILES`. Update that shared
contract rather than duplicating provider flags in skill docs.

Relevant profiles:
- `deep_review` — Gemini `arch` + `gaps` axes
- `gpt_general` — GPT-5.5 **medium** on `correctness` + `contracts`
- `formal_review` — GPT-5.5 **high** on opt-in `formal` axis only
- `mechanical_review` — GPT-5.5 low on `mechanical` (deep/full)
- `fast_extract` — mechanical extraction elsewhere

The script writes these artifacts:
- `shared-context.md` / `shared-context.manifest.json`
- `<axis>-output.md`
- `findings.json`
- `disposition.md`
- `verified-disposition.md`
- `coverage.json`

`coverage.json` is the stable machine-readable summary. Current top-level fields:
- `schema_version`
- `artifacts`
- `context_packet`
- `dispatch`
- `extraction`
- `verification`

## Context Assembly

`--context-files` accepts file specs of the form `path/file.py`,
`path/file.py:100-150`, or `path/file.py:100`.

For plan-close review packets, prefer:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

## Context Formatting

Before assembling context, check `/model-guide` for per-model prompting rules.
Key points:

- GPT-5.5 context should use XML `<doc id="..." title="...">` tags for document sections
- Gemini does better when the question and constraints come last
- Keep prompts direct; the shared review script handles the rest

## Extraction Defaults

Use `--extract` for normal user-facing reviews. Use `--extract --verify` for
plan-close packets or any review that needs an auditable coverage trail with
checked references. Default preset `standard` = 2× Gemini + 2× GPT-medium; add
`formal` explicitly for math-dense subparts.
