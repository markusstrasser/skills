# Supervision — direction vector over human corrections

Single source: `~/Projects/agent-infra/scripts/supervision_taxonomy.py` (types + regex tier).
Session parser: `supervision_session.py`. CLI: `supervision-kpi.py`.

## The objective is a vector, not a scalar

| Direction | Meaning | RSI response | Declining = good? |
|-----------|---------|--------------|-------------------|
| **RAISE_AUTONOMY** | Agent was timid (asked/deferred on reversible work) | Loosen, act | Yes — pure autonomy signal |
| **REDUCE_ERROR** | Agent was wrong | Correctness guardrail | Yes — quality signal |
| **GROW_COVERAGE** | Agent missed existing context | Add detector / grow recall | Yes — recall signal |
| **AMPLIFY_TASTE** | Agent missed taste/voice | Generate options, keep human judge | Ambiguous — production burden |

**Autonomy reading (conjunction):**
```
genuine gain == RAISE_AUTONOMY ↓  AND  (REDUCE_ERROR + GROW_COVERAGE) not rising
```

Never collapse these into one "wasted %" — opposite-sign corrections imply opposite fixes.

## Typed events (inspectable)

Each correction is a `SupervisionEvent` with:
- `type_id` — over_caution | rediscovery | error_correction | denial | repeated_instruction | taste_steer
- `direction` — one of the four above
- `method` — regex | emb | structural
- `evidence` — matched substring or seed (answerable: "why tagged over_caution?")

## Headline metrics (observe supervision mode)

| Metric | Definition |
|--------|------------|
| **correction_rate_pct** | taxonomy-classified events / user turns |
| **vector** | aggregated direction counts |
| **autonomy_reading** | genuine_gain \| mixed \| timidity_rising \| … |
| **AIR** | corrections within 3 turns after hook shown / hooks shown |
| **gross_load** | weighted sum — coarse total only, NOT the objective |

## Fix types (for synthesis)

For each direction with recurrence ≥3 across sessions:

| Fix type | When |
|----------|------|
| **HOOK** | Deterministic predicate (PreToolUse, Stop) |
| **RULE** | Checkable CLAUDE.md default |
| **DEFAULT** | Change default behavior |
| **SKILL** | Workflow encapsulation |
| **ARCHITECTURAL** | New script, detector, checkpoint system |

## Constraints

- Regex tier is deterministic ($0) — same taxonomy as `blindspot_miner` emb tier.
- Do not duplicate taxonomy regexes in consumers (principle #9).
- LLM synthesis proposes fixes; raw report JSON is source of truth.
- Do not propose fixes already in improvement-log / deployed hooks.

## Relationship to blindspot

| Lane | Method | Question |
|------|--------|----------|
| **supervision** (this mode) | taxonomy regex + structural | What corrections happened, by direction? |
| **blindspot** | emb-contrastive on same taxonomy | What loop misses did the human catch semantically? |

Different recall profiles — do not merge counts in digests.
