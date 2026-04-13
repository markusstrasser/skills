<!-- Reference file for modal skill. Loaded on demand. -->

# Question -> Source -> Status -> Spend

Use this pattern whenever you need to explain what happened in Modal without mixing runtime state and billing attribution.

## Contract

- `Question` - the thing you are trying to answer or run.
- `Source` - the smallest artifact that can answer it. Prefer one of: app logs, container logs, a volume file, a result JSON, a dashboard object, or a billing report.
- `Status` - the runtime state of the source artifact.
- `Spend` - the billing attribution for the run or stage.

## Rules

1. Keep `status` and `spend` separate in all notes and reports.
2. Do not infer one from the other.
3. Tag launches with `question_id`, `run_id`, and `stage` so logs and billing can be joined later.
4. Use logs or dashboards for status; use billing reports for spend.
5. If the source cannot be named, the question is still open.

## Reporting Template

```markdown
| Question | Source | Status | Spend | Notes |
|----------|--------|--------|-------|-------|
| ...      | app logs / bill / volume file | running / failed / done | $12.34 | ... |
```

## Practical Defaults

- For status: prefer `modal app logs --follow` or the Modal dashboard object view.
- For spend: prefer `modal billing report` grouped by tags, with `question_id`, `run_id`, or `stage`.
- For provenance: record the app name, container ID, volume path, or report URL rather than a paraphrase.
