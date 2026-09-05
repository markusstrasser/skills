# Research Output Formats and Provenance

Use when a research artifact is useful or requested. Quick answers are inline with a source citation and material uncertainty; they need no report template. Adapt the format to the question rather than filling empty sections.

## Standard memo example

```markdown
## [Topic] — Research Memo

**Question:** [what was asked]
**Tier:** Standard | **Date:** YYYY-MM-DD
**Ground truth:** [relevant prior knowledge, checked for currency]

### Claims Table
| # | Claim | Evidence | Confidence | Source | Status |
|---|---|---|---|---|---|
| 1 | ... | RCT / dataset | HIGH | [DOI/URL] | VERIFIED |
| 2 | ... | Inference | LOW | [URL] | INFERENCE |
| 3 | ... | None found | — | — | UNSOURCED |

### Key Findings
[Conclusion connected to the supporting evidence and its quality]

### What's Uncertain
[Unresolved questions and what would change the answer]
```

Deep reports also retain disconfirmation results, a verification log (tool/source checked vs training knowledge), and a search log (queries, tools, dates, hits/misses). [Adversarial reviews](adversarial.md) use a labeled case brief.

When evidence is insufficient, report the question, what was searched, what was not found, defensible partial findings, and the next source or observation that would help. Do not turn training knowledge or unverified leads into a confident sourced conclusion.

## Provenance vocabulary

Make the basis of substantive claims visible, using these tags where the artifact's convention calls for them:

| Tag | Meaning |
|---|---|
| `[SOURCE: url]` | Retrieved document |
| `[DATABASE: name]` | Reference database query; include record/query details |
| `[DATA]` | Own reproducible analysis |
| `[INFERENCE]` | Derived conclusion; state chain and assumptions |
| `[TRAINING-DATA]` | Model knowledge, not retrieved evidence |
| `[PREPRINT]` / `[FRONTIER]` | Unreplicated work |
| `[UNVERIFIED]` | Plausible claim not verified |
| `[UNSOURCED]` | Empirical claim without source provenance |
| `[SCITE: S:X C:Y M:Z]` | Citation-stance metadata, not a verdict |
| `[ESTIMATED]` | Generated estimate, not a sourced measurement |

Do not present inference as sourced fact or training knowledge as a retrieved source. In investigation/OSINT, use the [shared Admiralty grades](../../references/source-grading/SKILL.md) instead of tagging the same claim twice.

Put exact source wording in quotation marks with a citation; write the rest in your own indirect speech. State consequential source-quality information alongside the claim rather than hiding it in a composite rating.

For a number doing argumentative work, apply the [quantitative construction checklist](quant-bias-checklist.md): ledger, unit, base, window, gross/net status, and measurement versus model output. When defensible constructions differ, lead with their range. Scientific quantitative claims also follow [paper evidence checks](paper-evidence.md).
