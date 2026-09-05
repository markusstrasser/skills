# Paper Evidence and Citation Checks

Use when scientific papers support the answer. These checks apply to the claims being made; they do not require a full literature review for one factual lookup.

## Read the evidence

Locate academic metadata with `search_papers` or the authoritative publication/database record. Verify that DOI, PMID, title, authors, and date identify the intended paper. Check PMID and PDB identifiers against their actual databases; never trust a citation-shaped search result alone.

Fetch and read the relevant full text before citing a paper as ordinary support. With the research MCP, use `fetch_paper` then `get_paper` / `read_paper`; an accessible publisher, PMC, or arXiv full text is also valid. Check that the content was retrieved, not just a metadata row. If only an abstract is available, identify that access limit and restrict claims to what it supports.

For synthesis across papers, the corpus path is `search_papers` → `save_paper` → `fetch_paper` → `get_paper` → `prepare_evidence` → `ask_papers(use_rcs=True)`. Use it when corpus retrieval helps the task. Saving or delegating synthesis does not replace reading the evidence behind the conclusion.

If retrieval hangs or fails repeatedly, switch to a working primary-source route. See [tool recovery](tool-routing.md#retrieval-recovery) and [known issues](known-issues.md); transport failure is not a scientific negative. Do not purchase access or use credentials beyond the user's authorization.

## Grade support at the claim

Every empirical quantitative scientific claim needs a resolved DOI or PMID and the specific finding supporting it. An official trial registry or database record can support a registry/database claim directly. For an unresolved empirical claim, mark `[UNSOURCED]`; it should not drive a protocol or dose recommendation without explicitly acknowledging that gap.

Deduction is `[INFERENCE]` with its chain and assumptions; a reproducible conversion or analysis is `[DATA]`; an invented estimate is `[ESTIMATED]`. Established background facts do not need ritual citations, but specific numerical details and decision-relevant biological claims do.

Treat a returned paper-quality card as evidence. Surface its components rather than creating an aggregate score or traffic light:

- **`RETRACTED`:** do not use as valid support. A retraction can be discussed as such.
- **`CANDIDATE_GENE`:** do not treat pre-GWAS single-gene association studies as ordinary association evidence; name the veto. Preserve the PGx (CYP*, HLA, UGT) and mechanism-study exceptions.
- **`NON_HUMAN_ONLY`:** state organism and what transfer is and is not supported. Biological mechanism is not human clinical efficacy.
- **`CASE_REPORT_ONLY`:** establishes existence, not magnitude.
- Surface consequential design details: population, sample size, blinding, comparator, preregistration, single-center design, funding/COI, data availability, and replication.

For example: `RCT, n=200, human, double-blind, placebo, government-funded`; or `VETOED — candidate gene association study`. Explain any reliance on a vetoed result rather than silently treating it as normal support. For clinical/biological interpretation, use the [shared epistemics reference](../../references/epistemics/SKILL.md).

For claims asserting consensus, inspect supporting and conflicting later work. Use scite citation stance if available, reporting `[SCITE: S:X C:Y M:Z]` or `[SCITE: NO COVERAGE]`. Counts and automatic stance labels are leads to check, not substitutes for the underlying papers.

## Mechanical citation gate for memo artifacts

Before finalizing a memo with arXiv IDs or DOIs, run the existing checker:

```bash
uv run --no-project python3 ~/Projects/skills/research/scripts/verify_citations.py /absolute/path/to/memo.md
```

Use `--json` for structured output. In an isolated checkout, substitute that checkout's `research/scripts/verify_citations.py` path.

- **`hallucinated > 0` blocks finalization:** fix or remove the unresolved citation. Investigate an extraction defect before declaring a source fabricated.
- **`unreachable` is not `hallucinated`:** a transport failure is excluded from the rate; retry or verify through the primary source and record the outcome.
- `resolved_rate < 80%`, `arxiv_only_ratio > 60%`, and DBLP `venue-upgrade` candidates are advisory. Report them in the source log and act when useful; they do not create an approval gate.

The checker tests identifier existence and venue, not whether the identifier matches the claimed paper or supports the quoted result. Inspect the source for those checks. Compare the extracted citation count to the memo when known parser limitations apply; an empty extraction is not successful verification.

Historical rationale: `agent-infra/decisions/2026-06-19-autoresearch-grounding-imports.md`. Parser incidents are retained in [known issues](known-issues.md).
