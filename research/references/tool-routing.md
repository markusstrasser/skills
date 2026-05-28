# Research Tool Reference

Full tool descriptions for reference. Core routing is in SKILL.md — load this for tool details.

## Available Research Tools

Use whichever of these are available in the current project's `.mcp.json`:

| Tool | What it does | When to use |
|------|-------------|-------------|
| `mcp__selve__search` | Personal knowledge search | Prior work, conversations, notes — **always check first** if available |
| `mcp__duckdb__execute_query` | Query project DuckDB views | Local data — check before going external |
| `mcp__intelligence__*` | Entity resolution, dossiers, screening | Investigation targets (if configured) |
| `mcp__research__search_papers` | Semantic Scholar search (220M+ papers) | Canonical papers, citation counts, structured metadata. **No date filtering** — use Exa for recency |
| `mcp__research__save_paper` | Save paper to local corpus | After finding useful paper |
| `mcp__research__fetch_paper` | Download PDF + extract text | **Before citing any paper** |
| `mcp__research__read_paper` | Get full extracted text | Reading a fetched paper |
| `mcp__research__prepare_evidence` | Score paper chunks for relevance (RCS) | Before `ask_papers` — higher quality synthesis |
| `mcp__research__ask_papers` | Query across papers (Gemini 1M) | Synthesizing multiple papers. Set `use_rcs=True` for scored evidence. |
| `mcp__research__traverse_citations` | Discover related papers via citation graph | After finding seed papers — one-hop with overlap filtering |
| `mcp__research__extract_table` | Elicit-style structured extraction | Comparing findings across papers — column-based extraction |
| `mcp__research__list_corpus` | List saved papers | Check before searching externally |
| `mcp__research__verify_claim` | Verify factual claim via Exa /answer | High-stakes claims: numbers, stats, entity properties (~$0.005/call, cached 7d) |
| `mcp__research__export_for_selve` | Export for knowledge embedding | End of session, persist findings |
| `mcp__research__search_preprints` | bioRxiv/medRxiv date-range + keyword search | Preprint surveillance. `server="biorxiv"` or `"medrxiv"`, `days=7`, optional `category`. |
| `mcp__exa__web_search_exa` | Semantic web search | Non-obvious connections, expert blogs, recent work. **Recency enum: `24h`, `week`, `month`, `year`, `any` only — NOT `365d`/`90d`/`180d`.** |
| `mcp__exa__web_search_advanced_exa` | Advanced search (filters, deep, structured) | Entity enrichment, date-filtered research, domain-restricted search |
| `mcp__exa__company_research_exa` | Company intelligence | Business/financial research |
| `mcp__brave-search__brave_web_search` | Independent web index, free tier | Serial fallback when Exa is silent or contested. Note: Exa+Brave agree on ~95% of verdicts at the verdict level (κ=0.708, N=60 2026-05-19) — triangulating both rarely buys new signal except on panel-attribution debates where Brave's `count: 5` widens the domain spread. |
| `mcp__brave-search__brave_news_search` | Dedicated news search | Time-sensitive events (default 24h) |
| `mcp__perplexity__perplexity_search` | Raw web search results (Search API) | URL discovery, cheap fact-checking (~$0.005/call). No AI synthesis — ranked results with snippets. |
| `mcp__perplexity__perplexity_ask` | Grounded factual answer (Sonar Pro) | **Domain-dependent.** Empirically 5-0 vs Exa `/answer` on genomics precision (Mar 2026 N=5); BUT 30% precision on art-historical / scholar-attribution claims at N=60 (2026-05-19) — quibbles on framing rather than hallucinates. Cost ~$0.01-0.05/call. Use for biomedical precise-number claims; avoid for reception / attribution / scripture work where Exa or Brave are 80%+. Batch ergonomic safe at N≤10, risky at N≥25 (rubber-stamps user-supplied specifics). |
| `mcp__perplexity__perplexity_reason` | Chain-of-thought + web (Sonar Reasoning Pro) | Analytical "why" questions needing multi-step reasoning + evidence (~$0.05-0.15/call). |
| `mcp__perplexity__perplexity_research` | Deep multi-source report (Sonar Deep Research) | Literature-survey-scale questions. Slow (~30s+), expensive (~$0.15-0.50/call). |
| `mcp__scite__search_literature` | Citation-stance search (1.6B+ citations) | Disconfirmation, literature audits, checking if a claim is supported/contrasted. Returns Smart Citation snippets with stance. |
| `mcp__scite__search_patents` | Patent family search | Prior art, IP landscape, competitor patents, inventor/assignee tracking. Pro plan. |
| `mcp__scite__search_grants` | Grants search (NIH RePORTER, NSF, SBIR/STTR, Wellcome, EU) | Funder mapping, who's funded for what, award sizes. Pro plan. |
| `mcp__scite__search_clinical_trials` | ClinicalTrials.gov search | Trial design, status, outcomes. Overlaps `biomcp`/`biomedical.clinical_trial_search` — prefer those for trial-only queries; reach for scite's variant when joining trials with literature/citations in one session. Pro plan. |
| `mcp__scite__search_device510k` / `search_510k_summaries` | FDA 510(k) clearance metadata + full PDF text | DTC/LDT regulatory predicate work, substantial-equivalence reasoning, indications-for-use, predicate device discovery. **No equivalent elsewhere in the fleet.** Pro plan. |
| `mcp__scite__search_mhra` | UK MHRA safety alerts + field safety notices | UK drug/device safety communications, recalls, regulatory guidance. **No equivalent elsewhere in the fleet.** Pro plan. |
| `mcp__firecrawl__firecrawl_scrape` | JS-heavy page scraper | Financial dashboards, dynamic sites. Only if configured. |
| `mcp__context7__*` | Library documentation | API/framework questions |
| `mcp__parallel__parallel_task` | Deep web research with code-execution sandbox | Complex multi-step questions needing cross-referencing. Processor tiers: lite/core/ultra/ultra8x. 70-82% on DeepSearchQA. |
| `mcp__parallel__parallel_search` | Quick web-grounded lookup (lite tier) | Simple factual questions with citations (~$0.005/call). Alternative to verify_claim. |
| WebFetch | Fetch specific URLs | Known databases, filings, regulatory |

Not all tools exist in every project. User-scope MCPs (scite, perplexity, brave-search, exa, parallel) are available everywhere. `research` MCP (research-mcp) is per-project.

## Parallel vs Exa (empirical routing, 2026-04-07)

Benchmark claims and live routing should not be conflated.

- **Parallel benchmark strength:** DeepSearchQA-style multi-hop answer generation. This tests end-to-end reasoning over search/extract loops.
- **Exa strength:** exact-source discovery and targeted crawling. This is the better fit when the task is "find the exact paper / benchmark / official page and quote the right part."
- **Observed in genomics eval:** Exa consistently found the sharpest primary sources faster for hard-locus benchmarking, long-read PGx comparison, and CHIP assay-limit questions. Parallel core gave usable summaries, but often cited broader adjacent sources rather than the best source.
- **Routing rule:** if you are writing a memo and care which exact paper or webpage anchors the claim, start with Exa. If you are answering a broad multi-hop question and the exact source is less obvious upfront, consider Parallel core. Use `ultra` asynchronously only.

## EBF3 Benchmark — Tool-Class Routing (empirical, N=1)

Benchmarked academic-only vs websearch-only vs combined on a real genomics VUS question. Three findings:

**1. Websearch first for structured database lookups.**
Exa/Brave to query UniProt, gnomAD, MaveDB, ClinVar, DECIPHER — these are web databases, not literature. Academic tools return papers *about* these databases. Websearch found the exact UniProt domain boundary that academic missed (inferred from homology instead of querying directly).

**2. Academic tools for citation-verified literature.**
S2/PubMed produced zero hallucinated citations. Websearch hallucinated a PDB ID (doesn't exist), two year errors, and a self-contradiction. Combined hallucinated a journal+page. **Never trust a PMID or PDB ID from websearch without S2 verification.**

**3. Don't synthesize without database context.**
Combined's hallucination happened because it reasoned from training memory. When database facts (domain boundaries, frequencies, ClinVar entries) are in context from earlier queries, the model anchors on facts instead of inventing.

**Sequence:** (1) Websearch: database lookups → (2) Academic: literature → (3) Synthesize with both in context.

**Limitation:** N=1 (genomics VUS), single model. Websearch may outperform academic in fast-moving fields where S2 indexing lags.

## Cross-Source Verification Benchmark (N=60 stratified, 2026-05-19)

Larger, statistically rigorous follow-up to the EBF3 N=1. **Domain: gospel-reception facts** (artwork provenance, cinema specifics, scripture cross-references, scholar attribution) — NOT genomics; routing may differ for biomedical claims.

Method: 60 stratified claims × 4 engines × ground-truth grading (primary fetch + majority of independent indexes; Perplexity excluded as engine-under-evaluation). Wilson 95% CIs, McNemar pairwise, Cohen's κ between engines, inter-rater κ on the N=30 first half.

### Per-engine precision

| engine | strict precision | 95% CI | failure mode |
|---|---|---|---|
| Exa `web_search_exa` | **88.3%** | [77.8%, 94.2%] | rubber-stamps PARTIAL on attribution debates (~1 in 30); never false-strict |
| Brave `brave_web_search` | 86.7% | [75.8%, 93.1%] | rate-limits on parallel; `count: 5` catches panel-level nuance Exa flattens |
| Primary WebFetch (museum + Wikipedia) | 75.0%¹ | [61.2%, 85.1%] | 20% fetch failure at scale (museum URLs 403/404 — KHM, NG London, Met, Prado, AGO, Scuola San Rocco) |
| Perplexity Sonar Pro `high` single | 75.0% | [62.8%, 84.2%] | quibbles on framing ("insufficient library" not "no library") — 30% on context-scholar stratum |
| *Random-TRUE baseline* | *83.3%* | *—* | (sample is 83% TRUE-skewed; only Perplexity is reliably below baseline) |

¹ Primary N=48 (12 fetch failures of 60); lenient precision 89.6%.

**Statistical reality at N=60:**
- Brave-vs-Exa CI overlap completely; McNemar p=1.00 (51 of 60 verdicts agree). The two are **statistically indistinguishable** at this N.
- Perplexity-vs-Exa McNemar p=0.022 — the only pairwise comparison clearing p<0.05.
- Inter-rater κ = 0.716 (substantial) on N=30 first half; no TRUE↔FALSE swaps, grader bias doesn't drive headlines.

### Exa and Brave are NOT independent indexes (correction to prior routing claim)

Cohen's κ on pairwise verdicts:

| pair | κ | agreement |
|---|---|---|
| **Exa vs Brave** | **+0.708** | 95.0% — substantial; share most underlying evidence |
| Perplexity vs Exa | +0.195 | 80.0% — slight |
| Perplexity vs Brave | +0.173 | 78.3% — slight |
| Exa vs Primary | +0.130 | 61.7% — slight |

**Triangulating Exa + Brave buys very little new signal over either alone.** They agree on 57 of 60 verdicts; the divergences are valuable specifically for panel-attribution debates (e.g. Fra Angelico Bacio di Giuda, where Brave's deeper read caught that Baldovinetti contributed to 3 OTHER panels of the cycle, not this one). Use Exa as default; reserve Brave for serial fallback on contested attribution.

### Per-stratum routing (N=10/cell, strict precision)

| stratum | best engine | precision | notes |
|---|---|---|---|
| artwork-date | Exa or Brave | 100% [72, 100] | Primary degraded by 20% museum-URL fetch failures |
| artwork-attribution | tied 70% | all engines ~70% | Brave qualitatively catches panel-nuance |
| artwork-count | Exa | 80% [49, 94] | (N=30 Perplexity lead at 80% did NOT replicate at N=60) |
| cinema-fact | Exa or Brave | 100% [72, 100] | Primary silent on dialogue |
| scripture-greek | Exa or Brave | 100% [72, 100] | Primary URL often single-language Bible |
| **context-scholar** | **anything but Perplexity** | Perp 30% [11, 60] vs others 75-80% | Only stratum where Perplexity is reliably worse |

### Recommended routing (empirically supported, simpler than prior matrix)

1. **Default: Exa `numResults: 3-5`** — ~95% of reception/scholar claims resolve in one call. Cost ~$0.005/call.
2. **Tiebreaker: WebFetch Wikipedia-on-the-work** — when Exa snippets conflict or claim hinges on a single canonical page (Scrovegni wall, Contarelli installation date, Tenebrae responsory attribution). Prefer Wikipedia-on-the-work over museum URLs (the museum-URL fetch-failure rate is ~20% at scale).
3. **Serial Brave fallback** — for panel-attribution debates where Brave's wider domain spread (`count: 5`) catches what Exa flattens. ~1 in 30 entries.
4. **Image-vision Read** — only engine that catches wrong-file-in-place errors (image content vs caption claim drift). No web engine reads images. Confirmed unique value: 4 wrong-file catches in prior session (Polenov→Repin portrait, etc.).
5. **Avoid Perplexity for context-scholar claims** — 30% precision (upper CI 60% vs others' lower bound 49%). Useful elsewhere but reliably worst here.

### Batch-Perplexity ceiling

- **N ≤ 10 claims/batch: safe** (in this study, 9/10 vs single 8/10; batch hedged correctly on the contested Allegri-Mozart memory claim where single said TRUE).
- **N ≥ 25 claims/batch: risky** — rubber-stamps user-supplied numerical specifics (prior session: Tissot 365-gouaches claim returned TRUE in a 25-batch even though Brooklyn Museum page says 350).

### Perplexity cost discipline

`sonar-deep-research` (`perplexity_research`) is the cost sink — not search/ask. On the May 2026 billing cycle it was **~87% of Perplexity spend** ($82 of $94; reasoning tokens alone $47, fan-out search queries $22), while all the demoted `sonar-pro` calls totalled ~$12. Rules:
- **Never run `perplexity_research` at default `reasoning_effort`.** Set `medium` (or `low`); reserve `high` for questions that genuinely need it — reasoning tokens are the #1 line item.
- **Deep research is opt-in for broad / unknown-scope only.** Focused questions → `search_papers`→`fetch_paper` or a targeted Exa search, not a deep-research call that fans out to 80–160 searches per invocation.
- **Re-grade Perplexity Deep vs Exa Deep / Deep Max before defaulting either** — Exa Deep (~94% acc, ~11s) likely covers most of these cheaper.
- Prefer the **async API** for any background / scheduled deep-research dispatch.

Source: user Perplexity billing dashboard, 2026-05-28.

### Failure modes worth knowing

- **Pretool burst-hook fires at ~30 consecutive Exa calls.** Interleave a Read every ~6-9 searches in subagent dispatch.
- **Composer-attribution silent misdirection** — searching "Composer X Responsory Y" returns generic Tenebrae pages that don't disambiguate whether X actually set Y. Needs a separate targeted query (e.g. "Y composers"). Single case caught in N=60: subagent claimed Victoria didn't set "In Monte Oliveti"; Wikipedia 1585 list confirms he DID.
- **Spatial-orientation claims invert silently in prose** — north/south wall, recto/verso, left/right of altar are exactly the class where confident-sounding generation gets it backwards. Always tiebreaker-fetch.
- **Stylized-vs-literal interpretive claims** — "Antonello painted the Messina horizon from his own window" is the painterly reading; 2010 orographic studies place the view from Camaro hills. Strict literal verification flags this as PARTIAL; either is defensible depending on register.

### Class-imbalance caveat (worth knowing for future benchmarks)

Ground-truth distribution in this sample is ~83% TRUE — so the random-TRUE baseline (83.3%) sits inside every web-engine CI. Cannot strictly reject "always-TRUE = Exa" at p<0.05 at N=60. To get statistical separation between Exa/Brave/Primary:
- Either oversample PARTIAL/FALSE ground-truth claims (a class-rebalanced N=60 with 20/20/20 distribution would move the baseline to 33%)
- Or scale to N=200+ (CI half-width shrinks by ~√3 from N=60)

For routing decisions the qualitative findings (per-stratum precision, kappa, failure modes) are more useful than the strict-precision rankings. The N=60 study makes engine routing decisions, not engine *rankings*.

### Cost rollup for the benchmark itself

| pass | calls | cost |
|---|---|---|
| N=30 5-engine sweep + IRR | ~280 | ~$2.80 |
| N=30 → N=60 expansion | ~120 | ~$1.50 |
| 232-entry residual fact-check (Part C) | ~143 | ~$1.95 |
| **Total** | **~543** | **~$6.25** |

Source data: `/Users/alien/Projects/publishing/research/2026-05-19-engine-reliability-metric.md` (CIs, McNemar tables, kappa) + `2026-05-19-engine-process-observations.md` (per-engine behavior + failure-mode catalogue) + `verifications.md` (per-claim ledger, 468 entries).

## Evidence Base: Agent Reliability

- **Instructions alone ≠ reliability.** EoG (IBM, arXiv:2601.17915): perfect algorithm as prompt = 0% Majority@3 for 2/3 models. Architecture produces reliability.
- **Consistency is flat.** Princeton (arXiv:2602.16666): 14 models, 18 months, r=0.02. Same task + same model + different run = different outcome.
- **Documentation helps for novel knowledge, not known APIs.** Agent-Diff (arXiv:2602.11224): +19 pts for genuinely novel APIs, +3.4 for APIs in pre-training.
- **Simpler beats complex under stress.** ReliabilityBench (arXiv:2601.06112): ReAct > Reflexion under perturbations.

<!-- knowledge-index
generated: 2026-05-28T14:42:54Z
hash: ec64f60dddde

cross_refs: research/2026-05-19-engine-reliability-metric.md
table_claims: 22

end-knowledge-index -->
