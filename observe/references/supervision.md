# Observe: supervision

Use [transcript preparation](transcript-extraction.md) for the selected sessions and [candidate lifecycle](candidate-lifecycle.md) before staging findings. The KPI is a locator; inspect the raw turns before judging a session.

Human correction load as a **direction vector**, not a legacy "wasted %". Classification in
[supervision-waste.md](../lenses/supervision-waste.md); taxonomy in `agent-infra/scripts/supervision_taxonomy.py`.

`scripts/supervision-kpi.py --days N [--project P] --report …/supervision-report.json --output
…/supervision-sessions.jsonl`. Report the headline numbers: sessions, user turns,
**correction_rate_pct**, the **direction vector** (raise_autonomy · reduce_error · grow_coverage ·
amplify_taste), **autonomy_reading** (genuine_gain | mixed | timidity_rising | …), top sessions by
load with inspectable evidence strings, and AIR (corrections after hooks / hooks shown). Then
extract transcripts for the top 3-5 sessions by load and synthesize automatable patterns for each
direction with recurrence ≥3:

```
### [TYPE_ID]: [one-line description]
- **Direction:** RAISE_AUTONOMY | REDUCE_ERROR | GROW_COVERAGE | AMPLIFY_TASTE
- **Occurrences:** N (across M sessions)      - **Evidence:** [taxonomy evidence string]
- **Fix type:** HOOK | RULE | DEFAULT | SKILL | ARCHITECTURAL
- **Proposed fix:** [specific implementation]  - **Maintenance:** NONE | LOW | MEDIUM
```

Lead `digest.md` with the vector and autonomy_reading, **never a scalar waste %**. On `--days 7+`,
compare against the prior run: RAISE_AUTONOMY trending down *without* REDUCE_ERROR/GROW_COVERAGE
rising is genuine gain. Over-caution flat while an enforcing detector is active is a
detector-efficacy confound — check the control classes.
