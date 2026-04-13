<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Extraction Mechanics (Step 5)

Use this only when `--extract` was not passed to the review script and you need to
run extraction manually. In the normal closeout flow, the shared review script
handles extraction for you and emits `disposition.md` plus `coverage.json`.

## Why This Step Exists

Single-pass synthesis is lossy. The agent biases toward recent, vivid, or
structurally convenient ideas and silently drops others. In observed sessions,
users had to ask "did you include everything?" 3+ times — each time recovering
omissions. The EVE framework (Chen & Fleming, arXiv:2602.06103) shows that
separating extraction from synthesis improves recall +24% and precision +29%.

## Cross-Family Extraction

The review script already dispatches extraction to a different model family from
the reviewer and writes the extracted findings to `findings.json`.

If you customize the extraction prompt, keep it mechanical:

- extract every discrete recommendation, finding, or claim as a numbered list
- one item per line
- do not evaluate or filter

The source of truth for the extraction prompt is `review/scripts/model-review.py`.

## Anonymize During Disposition

Use anonymous labels (A1-An, B1-Bn) in the disposition table — not model names.
This prevents identity-driven bias during synthesis (Choi et al. arXiv:2510.07517
found model identity biases peer evaluation). Reveal model identities only in the
"Model Errors" section where you need to know which model to distrust.

```markdown
## Extraction: Reviewer A
A1. [Prediction ledger needed -- no structured tracking exists]
A2. [Signal scanner has silent except blocks -- masks failures]
A3. [DuckDB FTS preserves provenance better than vector DB]
...

## Extraction: Reviewer B
B1. [Universe survivorship bias -- S:5, D:5]
B2. [first_seen_date needed on all records for PIT safety]
B3. [FDR control mandatory -- 5000-50000 implicit hypotheses/month]
...
```

## Disposition Table

Every extracted item gets a verdict. No item left undispositioned.

```markdown
## Disposition Table
| ID  | Claim (short) | Disposition | Reason |
|-----|--------------|-------------|--------|
| G1  | Prediction ledger | INCLUDE -- Tier 1 | Both models, verified gap |
| G2  | Silent except blocks | INCLUDE -- Tier 6 | Verified in signal_scanner.py |
| G3  | DuckDB > vector DB | INCLUDE -- YAGNI | Constitutional alignment |
| P1  | Universe survivorship | INCLUDE -- Tier 4 | Verified, no PIT table exists |
| P2  | first_seen_date | INCLUDE -- Tier 1 | Verified, downloads lack it |
| P3  | FDR control | DEFER | Needs experiment registry first |
| P7  | Kubernetes deployment | REJECT | Scale mismatch (personal project) |
| ... | ... | ... | ... |
```

Valid dispositions: `INCLUDE`, `DEFER (reason)`, `REJECT (reason)`,
`MERGE WITH [ID]` (dedup).

## Coverage Check

Before proceeding to synthesis:

- count total extracted, included, deferred, rejected, merged
- if any ID has no disposition, stop and fix
- save extraction + disposition table to `$REVIEW_DIR/extraction.md`
- inspect `coverage.json` when the review came from the shared script; it records
  how many axes produced usable findings

This file is the checklist. If the user asks "did you include everything?" point
them here, not the prose.

## Multi-Round Extraction

When running multiple dispatch rounds (e.g., Round 1 architecture + Round 2 red
team):

1. Extract per round, not per synthesis.
2. Merge disposition tables across rounds before writing the final synthesis.
3. Never synthesize a synthesis. The final prose is written once from the merged
   disposition table.
4. Total coverage count in the final output should report round-level and merged
   totals.
