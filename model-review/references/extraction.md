<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Extraction Mechanics (Step 5)

Detailed extraction workflow. Use when `--extract` was NOT passed to the dispatch script and you need to extract manually. If `--extract` was used, skip this file -- the script already did it.

## Why This Step Exists

Single-pass synthesis is lossy. The agent biases toward recent, vivid, or structurally convenient ideas and silently drops others. In observed sessions, users had to ask "did you include everything?" 3+ times -- each time recovering omissions. The EVE framework (Chen & Fleming, arXiv:2602.06103) shows that separating extraction from synthesis improves recall +24% and precision +29%.

## Cross-Family Extraction

Use fast models for extraction -- this step is mechanical. Dispatch extraction to a fast model from a *different family* than the reviewer to avoid self-preference in what gets extracted (Wataoka NeurIPS 2024: same-family preferentially surfaces claims written in its style).

```bash
# Extract Gemini's review with GPT-5.3 Instant (cross-family extraction)
llmx chat -m gpt-5.3-chat-latest --stream --timeout 120 \
  -f "$REVIEW_DIR/gemini-output.md" \
  -o "$REVIEW_DIR/gemini-extraction.md" "
<system>
Extract every discrete recommendation, finding, or claim as a numbered list. One item per line. Do not evaluate or filter -- extract mechanically.
</system>

Extract all discrete ideas from this review."

# Extract GPT's review with Flash (cross-family extraction)
llmx chat -m gemini-3-flash-preview --timeout 120 \
  -f "$REVIEW_DIR/gpt-output.md" \
  -o "$REVIEW_DIR/gpt-extraction.md" "
<system>
Extract every discrete recommendation, finding, or claim as a numbered list. One item per line. Do not evaluate or filter -- extract mechanically.
</system>

Extract all discrete ideas from this review."
```

## Anonymize During Disposition

Use anonymous labels (A1-An, B1-Bn) in the disposition table -- not model names. This prevents identity-driven bias during synthesis (Choi et al. arXiv:2510.07517 found model identity biases peer evaluation). Reveal model identities only in the "Model Errors" section where you need to know which model to distrust.

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

Valid dispositions: `INCLUDE`, `DEFER (reason)`, `REJECT (reason)`, `MERGE WITH [ID]` (dedup).

## Coverage Check

Before proceeding to synthesis:
- Count: total extracted, included, deferred, rejected, merged
- If any ID has no disposition, stop and fix
- Save extraction + disposition table to `$REVIEW_DIR/extraction.md`

This file is the checklist. If the user asks "did you include everything?" -- point them here, not the prose.

## Multi-Round Extraction

When running multiple dispatch rounds (e.g., Round 1 architecture + Round 2 red team):

1. **Extract per round, not per synthesis.** Each round's outputs get their own extraction pass (G1-Gn for round 1 Gemini, G2.1-G2.n for round 2 Gemini, etc.).
2. **Merge disposition tables across rounds** before writing the final synthesis. Dedup with `MERGE WITH [ID]`.
3. **Never synthesize a synthesis.** The final prose is written once from the merged disposition table. Don't compress round 1's synthesis -- compress round 1's raw extraction alongside round 2's raw extraction.
4. **Total coverage count** in the final output: "R1: 47 items extracted, R2: 38 items extracted. Final: 85 total, 62 included, 14 deferred, 9 rejected."
