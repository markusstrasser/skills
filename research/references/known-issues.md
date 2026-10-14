# Research — Issue History

Append-only incident history. Entries describe the observed run and may be stale; inspect the current tool or parser before applying a workaround. Record corrections as new entries. The current upkeep helper writes here, not into SKILL.md.

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-09] fetch_paper hangs indefinitely on direct arXiv DOI; parallel fetch also serial-locks after first item, requiring termination and direct arXiv PDF fallback**

- **[2026-07-10] mcp__research__fetch_paper can hang beyond 60s on an arXiv PDF; terminate the transport, then use the primary-source browser or direct PDF tooling instead.**

- **[2026-07-14] 2026-07-14: mcp__research__search_papers backend=s2 hung over 45s on exact new arXiv id 2607.07508; direct primary arXiv PDF worked.**

- **[2026-08-12] fetch_paper hung >180s on DOI 10.1097/FPC.0b013e328012b8e4; an existing metadata-only DOI also returned immediately without fetching paper.pdf**

- **[2026-08-17] Exa web_search_advanced_exa date filter unreliable for category=publication (null dates, 2024/25 leakage) — for dated arXiv sweeps use the arXiv Atom API with submittedDate ranges (2026-08-17 design-agents lane)**

- **[2026-08-17] verify_citations.py regex misses bare arXiv IDs like "2607.20767" without an "arXiv:" prefix — reports vacuous PASS; curl-loop the abs pages as backstop until fixed (2026-08-17)**

- **[2026-08-18] verify_citations.py truncates old-style Elsevier DOIs containing parens (10.1016/S0160-2896(03)00053-9 -> "10.1016/S0160-2896(03)" flagged HALLUCINATED); regex needs paren-aware DOI matching — manually curl-resolve paren DOIs until fixed (2026-08-18)**

- **[2026-08-24] fetch_paper 0/8 on 2026 open-access DOIs (Nature/BMC/MDPI/Cambridge: Sci-Hub has no 2026 content, Unpaywall missed; 3 of the 8 hung >120s). Working route for anything with a PMCID: EuropePMC `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML` (6/6, no wall; S2 `search_papers` returns the PMCID). Publisher HTML via urllib → 3 KB cookie walls; bioRxiv 429; Sage/T&F 403; `crawling_exa` OK on nature.com/mdpi/BMC HTML but times out on Springer PDFs and OSF downloads (plain `curl -L` gets the OSF PDF). `search_preprints` returned [] on 3 well-formed queries the same day (2026-08-24, iq-sex-differences)**

- **[2026-09-01] 2026-09-01: arXiv export API silently IGNORES parenthesized OR-groups in search_query — (abs:A OR abs:B) AND abs:C returns unfiltered noise; a noisy result set is a BROKEN QUERY, not a negative. Use simple two-term ANDs or intersect client-side.**

- **[2026-09-02] references/source-grading is named by SKILL.md but absent from the installed research references directory (2026-09-02 Eileen Gu claim audit)**

- **[2026-09-05] RESOLVED pointer defect from 2026-09-02:** the source-grading and epistemics companions live at shared `~/Projects/skills/references/{source-grading,epistemics}/SKILL.md`. The research entrypoint and new evidence/output references now link to those actual files. The earlier missing-local-reference report remains above as evidence.

- **[2026-09-16] cdc.gov and cis.org answer curl with 403 (CDC PDFs via stacks.cdc.gov or NCBI Bookshelf, cis.org via Exa); census.gov QuickFacts returns a JS shell (use the Census API); www2.census.gov, nber.org, bjs.ojp.gov, ussc.gov and meps.ahrq.gov allow plain curl**

- **[2026-09-25] research-mcp `ask_papers`, `prepare_evidence` and `extract_table` failed for two reasons in turn: Gemini 3.x thinking used up the 256-token scoring cap, so `use_rcs` answered "No relevant evidence" on answerable questions (2026-08-24, 2026-09-16; fixed 39c53fb), and the critique-only key policy left no `GEMINI_API_KEY` ("No API key was provided"). Since research-mcp b712e03 all three run on Claude through `llmx chat --subscription` (no key; minutes, not seconds, for many papers; llmx exit 6 = plan limit, do not retry). `deep_research` still needs `GEMINI_API_KEY`. Marker-modal parses now report `llm_errors`; a nonzero count means Gemini cleanup failed and the text is the non-LLM parse (0e9a8dc).**

- **[2026-09-28] RESOLVED citation-checker response crash:** `verify_citations.py` aborted an entire genomics memo check when advisory DBLP returned non-JSON. DBLP malformed/empty/schema and transport failures now preserve resolved DOI status and emit `[DEGRADED]` in JSON notes and the brief; malformed Crossref responses become `unreachable`. Deterministic regressions live in `research/scripts/test_verify_citations.py` alongside the existing live DOI controls. Separate extraction defect remains open: bioRxiv `v1.full` URL suffixes can be mistaken for part of a DOI; cite the canonical DOI URL until host-aware extraction is repaired.

- **[2026-10-13] 2026-10-13: research MCP fetch_paper failed on arXiv IDs 2608.20318 and 2609.19799 (researcher fell back to curl arxiv.org/pdf + pdftotext); Exa web_search_advanced contextMaxCharacters did not cap output (5/9 calls overflowed to files). Source: agent-infra research/2026-10-13-*.md search records.**

- **[2026-10-13] RESOLVED citation-checker blind spots: verify_citations.py matched only arXiv-prefixed IDs, so memos citing bare IDs (**2610.07625**) passed as "vacuous — 0 citations" (4 memos, 70+ IDs); and 6 parallel workers drew arXiv HTTP 429 on 25 IDs, reported unreachable. Fix: ARXIV_BARE_RE with YYMM guard; serialized arXiv calls at 3 s with 429/503 backoff. Regression: test_verify_citations.py ExtractionTests + ArxivThrottleTests.**

- **[2026-10-14] RESOLVED fetch_paper outage, 2026-09-23 → 2026-10-14:** the research-mcp venv lost `modal` (a lockfile upgrade dropped the undeclared dependency), so the default parser failed on every PDF and the error read "Could not download PDF". About 155 of 162 fetches failed across 21 sessions, agents treated them as paywalls, and none flagged the outage. Fixed in research-mcp a6af825 (modal declared) and 5bde64f (each failed source is now named, and parse errors propagate). The 2026-10-13 arXiv failures above (2608.20318, 2609.19799) were this outage. Outputs written during the window were re-checked against full text on 2026-10-14. Lesson: a fetch error that lists the same failure for every source is a tool fault, not a paywall.
- **[2026-10-14] RESOLVED metadata-only cache hit (2026-08-12, second half):** `fetch_paper` returned a stored record that had no paper.pdf and no parse as a cache hit; 655 of 20,977 corpus records were metadata-only. It now downloads in that case (research-mcp f00d1ce).
- **[2026-10-14] Wrong paper ingested under a DOI:** a Sci-Hub mirror served "Polymetry and Metaphysics in F. T. Prince" for 10.1093/oep/gpz057 (Gunadi), and it was stored as that paper. Downloads now must show the DOI or most of the Crossref title words in their first two pages, else the next source is tried (research-mcp 1f6ff58). A sweep of 152 PDFs downloaded since 2026-09-23 found no other mismatch.
- **[2026-10-14] PARTLY ADDRESSED 2026 open-access gap (2026-08-24):** `fetch_paper` now tries OpenAlex's cached PDFs after Unpaywall (content.openalex.org, $0.01 per PDF, needs OPENALEX_API_KEY; research-mcp 93bfc42). The EuropePMC PMCID route above remains the fallback.
- **[2026-10-14] RESOLVED search_preprints scanned one page:** the bioRxiv API pages 30 records but the code assumed 100, so a keyword search scanned 30 of about 1,500 records in the window. It now pages through all of them and reports `matched`, `scanned`, `total_in_window` and `complete` (research-mcp 3baa8ea). Empty preprint searches before 2026-10-14 are not negatives.
- **[2026-10-14] RESOLVED Marker Gemini cleanup ran with a dead key:** every October marker-modal parse logged API_KEY_INVALID and kept Marker's non-LLM text under a `gemini-3_8-flash` parser id. The Modal secret was renewed after the operator lifted the Gemini critique-only policy; the affected parses were re-parsed.
