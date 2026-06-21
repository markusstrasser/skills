<!-- Reference: mechanical promotion gates. Loaded on demand. -->
# Promotion Gates (deterministic)

LLM lanes **propose** candidates; `observe_gates.py` **decides** promotion.

## Mandatory before any `improvement-log.md` write

```bash
OBSERVE_ARTIFACT_ROOT="${OBSERVE_ARTIFACT_ROOT:-$HOME/Projects/agent-infra/artifacts/observe/<run>}"
python3 "${CLAUDE_SKILL_DIR}/scripts/observe_gates.py" preflight --artifact-root "$OBSERVE_ARTIFACT_ROOT"
```

Read `preflight.json`:
- `promotions_allowed=false` → **no** `[ ]` promotions from agentlogs lanes; digest must banner.
- `saturation.saturated=true` → no new promotions unless `promotion-verdicts` has novel `promote` rows.

## Gate table (`observe.promotion_verdict.v1`)

| Gate | Pass condition |
|------|----------------|
| `recurrence` | `recurrence>=2` OR ≥2 distinct `sessions` |
| `session_manifest` | every `sessions[]` prefix in `input.md` / `codex.md` manifest |
| `existing_coverage` | `novel` for `[ ]`; `matched` → `obs` or suppress |
| `checkable` | `checkable:true` required for `[ ]` |
| `indexer_health` | failures/supervision/blindspot require `health.indexer_ok` |

## Verdict → sink

| verdict | improvement-log glyph |
|---------|----------------------|
| `promote` | `[ ]` + `maintain-candidates.json` row |
| `obs` | `[obs]` |
| `needs_evidence` | stay in `candidates.jsonl` only |
| `suppress` | append `state:suppressed` row |

## Failures lane extra rule

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/scan_tool_failures.py" --days 21 --json > failures.json
```

Promote only clusters with `invoker_primary=interactive_agent` (or `mixed` with interactive ≥ harness).
Do **not** attribute harness/cron failures to agent bash nudges.

## Pipeline order (deterministic-first)

1. `observe_gates.py health` (or full `preflight` at end)
2. `scan_tool_failures.py` → `failures.json` + signals
3. `blindspot` / `corrections` extractors
4. LLM lanes (sessions, supervision, drift) — explain clusters, don't invent infra
5. `validate_session_ids.py` on any model output
6. `observe_gates.py preflight` → `promotion-verdicts.jsonl`
7. `digest.md` from template (`references/digest-template.md`)
8. Promote **only** rows with `verdict=promote`
