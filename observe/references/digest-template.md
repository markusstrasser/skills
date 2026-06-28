# Observe digest template — metric slots are NOT interchangeable

Lead with **data validity**, then deterministic lanes, then LLM lanes.

```markdown
# Observe — {date} ({scope})

## Data validity
- **Indexer:** {indexer_ok} (last: {last_index_at}, status={last_index_status})
- **Promotions allowed:** {promotions_allowed} — see `preflight.json`
- **Saturation:** {saturated} (id_overlap={id_overlap}, token_overlap={token_overlap})

> If `promotions_allowed=false`, counts from failures/supervision/blindspot are **caveated**, not promotable.

## Metric legend (do not merge columns)
| Slot | Source | Definition |
|------|--------|------------|
| failures clusters | `scan_tool_failures.py` | Launch-failure signatures; `fails` = distinct tool_calls |
| invoker | failures JSON | `interactive_agent` vs `harness` — promote agent fixes only on interactive-primary |
| supervision vector | `supervision-kpi.py --report` | Direction vector (raise_autonomy / reduce_error / grow_coverage / amplify_taste) + correction_rate_pct — **not** a scalar waste % |
| blindspot pool | `blindspot_miner.py` | emb-contrastive loop-miss — **not** same as supervision CORRECTION |
| promotable | `promotion-verdicts.jsonl` | `verdict=promote` after `observe_gates.py preflight` only |

## Deterministic findings (Tier 0)
### Failures (`failures.json`)
{table: cluster | days | fails | invoker_primary | sample}

### Blindspot digest (link)
{path to .claude/blindspot-digest.md or lane digest}

## LLM lane summaries (Tier 1 — verify before promote)
{sessions, supervision, drift — no numeric merge with blindspot}

## Promotion queue (`promotion-verdicts.jsonl`)
| candidate_id | verdict | gates |
|--------------|---------|-------|

Only `verdict=promote` + `preflight.promotions_allowed=true` → `improvement-log.md` `[ ]`.
`verdict=obs` → `[obs]` or suppress. Never promote from digest prose alone.
```
