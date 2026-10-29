# Research Tool Routing

Use this reference when the source route is unclear or retrieval fails. Discover tools available in the current session and read their schemas; the names below identify capabilities, not a guarantee that every tool is installed. A known primary source can be read directly without a search pipeline.

## Route by evidence need

| Need | Preferred route |
|---|---|
| Prior work or personal context | Relevant local files, configured knowledge search, or saved corpus; avoid redoing a completed pass |
| Factual source discovery | Exa, then Brave if available and the first source is missing or contested |
| A claim to verify | Primary source or official database; `verify_claim` can locate supporting evidence |
| Academic literature | `search_papers`, verify metadata, then primary full text; [paper evidence checks](paper-evidence.md) |
| Recent publications | `search_papers` with `published_after`/`published_before` (S2, OpenAlex and alphaXiv honour them; EuropePMC does not), then check dates in the primary record; Exa `category:"publication"` only when accepted by the current schema |
| Recent biomedical preprints | `search_preprints` if available, or the server's own dated records; read its `complete` and `scanned`/`total_in_window` fields before treating no hits as none |
| UniProt / gnomAD / ClinVar / PDB facts | Query the relevant database; paper search returns papers about the database |
| Citation stance | scite `search_literature` if available; inspect the supporting/contrasting source papers |
| Patents / grants / trial or device records | The authoritative register; configured scite tools can assist discovery |
| What is new in an ML/CS area (last days) | `frontier scan --lens <name>` (arXiv, HF, HN, lab feeds, citations of exemplar papers; ranked top 12) and `frontier feed --lens <name>` (repos the lens's people starred); `frontier lenses` lists lenses, `~/Projects/frontier/README.md` explains them |
| News or events | Date-anchored news search and the original source; distinguish publication date from event date |
| Structured entity enrichment | Exa deep search and `outputSchema` if supported; retain per-field source pointers |
| Broad, multi-hop question | A configured Parallel/deep-research tool can help; exact-source questions usually start with targeted search |
| API or framework details | Current official documentation or a configured documentation tool |

The operator's established web preference is Exa then Brave. Using two engines does not establish independent evidence: trace whether their sources share an upstream source. Historical routing experiments and spending observations are in [tool-history.md](tool-history.md); they are not current performance guarantees.

## Cost and breadth

Prefer a targeted source search for a focused question. Large autonomous research calls can fan out far beyond the visible request; inspect current pricing and effort options before selecting one. For a justified `perplexity_research` call that accepts `reasoning_effort`, use `medium` or `low` unless the question specifically needs more. Do not invoke a paid service merely to fill a workflow slot; follow the user's existing spend authorization.

The retained Perplexity precise-number niche came from a small biomedical benchmark. Use it as an optional fallback after source discovery misses, not as authority for an answer. Verify the actual number against a primary source. Full old tool tables, costs, and benchmark limitations remain in the historical reference.

## Retrieval recovery

A failed or hanging backend says nothing about whether the paper exists or what its results mean. Switch early after repeated transport failure; do not perform multiple rounds of the same unsuccessful route. Keep the evidence-access limit visible.

- If S2 is failing, try an available alternate academic backend such as OpenAlex, or a primary PubMed/publisher/arXiv record. Verify the accepted argument with the current schema.
- Read `fetch_paper`'s `text_source`, `metadata_warning` and `quality_status` fields. Full text came from a parse when `text_source` starts with `parsed.`; `pymupdf_raw:` is the degraded last resort. A `quality_status` of `failed` or `degraded`, or a `retraction_check` other than `complete`, means the retraction status is unknown, not clean.
- A download error lists every source tried and why it failed. If every source fails the same way, or the error names a missing module or parser, the tool is broken: report it as a tool defect and do not record the paper as paywalled. From 2026-09-23 to 2026-10-14 a missing dependency made every fetch fail as "Could not download PDF", and no agent noticed (see [known issues](known-issues.md)).
- Check that fetched text is the paper you asked for (title, authors) before using it. Since 2026-10-14 the downloader rejects PDFs that show neither the DOI nor the registered title; scans and DOIs without a Crossref title still pass unchecked.
- For a PMCID, EuropePMC's public full-text endpoint is `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML`. PubMed's full-text links and EuropePMC's `fullTextUrlList` can reveal institutional or green-OA copies absent from the downloader's first result.
- To discover those links from a PMID, inspect `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<PMID>%20AND%20SRC:MED&resultType=core&format=json`.
- Prefer an accessible official repository or publisher copy. A configured crawler may retrieve public text when the ordinary downloader fails. Save the accessed text and its source URL when it becomes evidence.
- For genuinely restricted full text, use institutional access only within the user's authorization or report the limit. Do not purchase a paper or treat an access-control challenge as permission to bypass it.

For AI/ML and other arXiv topics, where S2 keyword search often returns nothing, use `search_papers` with `backend="alphaxiv"`: full-text keyword search whose hits carry page-numbered match snippets, with inclusive `published_after`/`published_before` bounds. Use `alphaxiv_embedding` for plain-language semantic queries. The pools are fixed server-side, at about 25 and 15 hits.

For dated arXiv searches, verify the returned dates and query semantics. Historical Exa date-filter leakage and arXiv OR-group failures are recorded in [known issues](known-issues.md). A noisy result set can be a malformed or ignored query, not a negative scientific result.

The [historical retrieval ladder](tool-history.md#fetch_paper-failure-recovery--green-oa--cloudflare-retrieval-ladder) preserves the 2026-07-04 green-OA incident and exact provider-specific observations. Read it only when that recovery path applies.
