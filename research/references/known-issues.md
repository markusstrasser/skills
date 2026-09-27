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

- **[2026-09-25] research-mcp `ask_papers`, `prepare_evidence` and `extract_table` failed for two reasons in turn: Gemini 3.x thinking used up the 256-token scoring cap, so `use_rcs` answered "No relevant evidence" on answerable questions (2026-08-24, 2026-09-16; fixed 39c53fb), and the critique-only key policy left no `GEMINI_API_KEY` ("No API key was provided"). Since research-mcp b712e03 all three run on Claude through `llmx chat --subscription` (no key; minutes, not seconds, for many papers; llmx exit 6 = plan limit, do not retry). `deep_research` still needs `GEMINI_API_KEY`. Marker-modal parses now report `llm_errors`; a nonzero count means Gemini cleanup failed and the text is the non-LLM parse (0e9a8dc).**

- **[2026-09-28] RESOLVED citation-checker response crash:** `verify_citations.py` aborted an entire genomics memo check when advisory DBLP returned non-JSON. DBLP malformed/empty/schema and transport failures now preserve resolved DOI status and emit `[DEGRADED]` in JSON notes and the brief; malformed Crossref responses become `unreachable`. Deterministic regressions live in `research/scripts/test_verify_citations.py` alongside the existing live DOI controls. Separate extraction defect remains open: bioRxiv `v1.full` URL suffixes can be mistaken for part of a DOI; cite the canonical DOI URL until host-aware extraction is repaired.
