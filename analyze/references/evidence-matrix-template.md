<!-- Reference file for competing-hypotheses skill. Loaded on demand. -->

# Evidence Matrix Template

## Prediction Table (Phase 3)

Before querying any data, fill in predicted values for each hypothesis:

| Evidence | If H1 | If H2 | If H3 |
|----------|-------|-------|-------|
| Metric A | Expected value | Expected value | Expected value |
| Metric B | Expected value | Expected value | Expected value |

For each cell, assign P(evidence | hypothesis) as a number in (0, 1).
These are LIKELIHOODS, not posteriors. They answer: "If this hypothesis were true, how likely would we see this evidence?"

## Report Evidence Summary (Phase 7)

| # | Evidence | Finding | Most Supports | Source |
|---|----------|---------|---------------|--------|
| 1 | ... | ... | H1/H2/H3 | [DATA]/Admiralty |
| 2 | ... | ... | H1/H2/H3 | [DATA]/Admiralty |

## Report Structure

1. Question framing (from Phase 1)
2. ACH Matrix (from Phase 5)
3. Evidence summary table (above)
4. Verdict: Surviving hypothesis (posterior), Killed hypotheses (why), Next steps
