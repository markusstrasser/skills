# Research Tool Reference

Full tool descriptions, routing logic, and search strategies. Loaded on demand from SKILL.md.

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
| `mcp__research__prepare_evidence` | Score paper chunks for relevance (RCS) | Before `ask_papers` for focused questions — higher quality synthesis |
| `mcp__research__ask_papers` | Query across papers (Gemini 1M) | Synthesizing multiple papers. Set `use_rcs=True` for scored evidence path. |
| `mcp__research__traverse_citations` | Discover related papers via citation graph | After finding seed papers — one-hop references/citations with overlap filtering |
| `mcp__research__extract_table` | Elicit-style structured extraction | Comparing findings across papers — column-based extraction in parallel |
| `mcp__research__list_corpus` | List saved papers | Check before searching externally |
| `mcp__research__verify_claim` | Verify factual claim via Exa /answer | High-stakes claims: numbers, stats, entity properties. Single-call, cached 7d |
| `mcp__research__export_for_selve` | Export for knowledge embedding | End of session, persist findings (if configured) |
| `mcp__paper-search__search_arxiv` | arXiv search | Preprints — flag as `[PREPRINT]` |
| `mcp__paper-search__search_pubmed` | PubMed search | Clinical/medical literature |
| `mcp__paper-search__search_biorxiv` | bioRxiv/medRxiv search | Biology/medical preprints |
| `mcp__exa__web_search_exa` | Semantic web search | Non-obvious connections, expert blogs, recent work |
| `mcp__exa__web_search_advanced_exa` | Advanced search (filters, deep, structured) | Entity enrichment (`type: "deep"` + `outputSchema`), date-filtered research, domain-restricted search |
| `mcp__exa__company_research_exa` | Company intelligence | Business/financial research |
| `mcp__brave-search__brave_web_search` | Independent index search | Triangulation with Exa (different index). Fallback when Exa rate-limits. |
| `mcp__brave-search__brave_news_search` | Dedicated news search | Time-sensitive events (default 24h). Better than Exa category filter for breaking news. |
| `mcp__perplexity__perplexity_ask` | Grounded factual answer | Quick "What is X?" — one call, cited. Saves search→fetch→synthesize. |
| `mcp__perplexity__perplexity_research` | Deep multi-source report | Comprehensive topic surveys. Alternative to Exa deep_researcher. Slow (~30s+). |
| `mcp__perplexity__perplexity_reason` | Chain-of-thought + web | "Why did X happen?" — analytical questions needing reasoning + evidence. |
| `mcp__perplexity__perplexity_search` | Raw web results | Third search source. Use when you want to control synthesis yourself. |
| `mcp__firecrawl__firecrawl_scrape` | JS-heavy page scraper | Financial dashboards, dynamic sites that WebFetch/Exa crawling can't handle. |
| `mcp__firecrawl__firecrawl_extract` | Structured data extraction | JSON Schema extraction from web pages. Company filings, earnings data. |
| `mcp__firecrawl__firecrawl_crawl` | Recursive site crawl | Investor relations sections, filing indexes. |
| `mcp__firecrawl__firecrawl_map` | URL discovery | "What pages exist on this site?" before crawling. |
| `mcp__scite__search_literature` | Citation-stance search (1.6B+ citations) | Literature audits, disconfirmation search, checking if a claim is supported/contrasted in the literature. Returns Smart Citation snippets with stance classification (supporting/contrasting/mentioning). |
| `mcp__context7__*` | Library documentation | API/framework questions |
| WebFetch | Fetch specific URLs | Known databases, filings, regulatory |
| WebSearch | General web search | News, grey literature |

Not all tools exist in every project. User-scope MCPs (scite, paper-search, perplexity, brave-search, exa) are available in all projects. Project `.mcp.json` has project-specific MCPs.

**Critical rule:** `fetch_paper` then `read_paper` BEFORE citing. Abstracts are not primary sources.

**S2 strengths (with API key):** 220M+ papers, structured metadata (citation counts, venues, DOIs), citation graph traversal, OpenAlex fallback. Best for: finding canonical papers, citation analysis, paper-to-paper discovery. Rate limit with key: 1 req/sec (vs 100/5min free). **S2 gotcha:** No date filtering. Use Exa for "recent papers on X." S2 API key set via `S2_API_KEY` env var in `~/.env`.

## Search Routing (Full)

- **Factual lookup:** Exa search + WebFetch, or `verify_claim` (Exa /answer, cached 7d).
- **Semantic discovery:** Exa remains primary (neural search, find_similar, categories).
- **Entity enrichment:** `web_search_advanced_exa` with `type: "deep"` + `outputSchema`. Offloads extraction to Exa's agents — structured JSON with per-field citations comes back directly. No post-hoc LLM extraction needed.
- **High-recall queries:** `web_search_advanced_exa` with `type: "deep"` + `additionalQueries`. Generate 2-3 domain-specific query variations from your context. Exa searches all in parallel, merges + ranks.
- **News/events:** `brave_news_search` for last 24h-7d. Exa with date filter for older.
- **Triangulation:** For high-stakes claims, use Exa + Brave (confirmed independent indexes). Perplexity is NOT confirmed independent — don't use for triangulation.
- **Structured extraction from URLs:** `firecrawl_scrape` or `firecrawl_extract` for specific URLs with JSON schema.
- **Rate-limited:** If Exa returns 429, fall back to `brave_web_search`.

## Perplexity — expensive, use selectively ($0.14/call avg)

Perplexity Sonar is ~5x more expensive per query than Exa+WebFetch. Don't use for breadth-first search or routine lookups. Use only when it's the decisive tool:

- **`perplexity_reason`:** Complex "why" questions where you need reasoning + grounded evidence in one call. Not for simple facts.
- **`perplexity_research`:** Deep topic surveys where Exa Research isn't available or you need a second opinion on a complex synthesis. Slow (~30s+), expensive.
- **`perplexity_ask`:** Only when you need a quick synthesized answer AND don't want to spend 3 tool calls on search→fetch→synthesize. Not the default for factual lookups — use Exa/Brave first.
- **`perplexity_search`:** Don't use. Exa/Brave are better raw search engines with confirmed independent indexes.

## Tool-Class Routing (empirical — EBF3 benchmark, 2026-03-03)

Benchmarked academic-only vs websearch-only vs combined on a real genomics VUS question (N=1, Sonnet, 15 turns each). Three empirical findings that change tool selection:

**1. Websearch first for structured database lookups.**
Use Exa/Brave to query UniProt, gnomAD, MaveDB, ClinVar, DECIPHER — these are web databases, not literature. Academic tools (S2/PubMed) return papers *about* these databases, not the data itself. In the benchmark, websearch found the exact UniProt domain boundary (Pro263 = IPT/TIG N-terminus) that academic missed entirely because it inferred from EBF1 homology instead of querying EBF3 directly.

**2. Academic tools for citation-verified literature.**
S2/PubMed produced zero hallucinated citations. Websearch hallucinated a PDB ID (3MUJ doesn't exist), two year errors, and a self-contradiction. Combined hallucinated a journal+page (real author, wrong journal). The failure pattern: websearch tools synthesize from training data + web snippets and confabulate citation details. **Never trust a PMID or PDB ID from websearch without verification via S2 or the actual database.**

**3. Don't run combined without database context.**
Combined's citation hallucination happened because it reasoned from training-data memory about a less-indexed paper. When database facts (domain boundaries, population frequencies, prior ClinVar entries) are already in context from earlier queries, the model doesn't need to invent. Feed websearch findings into your synthesis step.

**Practical sequence for variant/gene research:**
1. Websearch: UniProt domain boundaries, gnomAD constraint, MaveDB check, ClinVar entries
2. Academic: PubMed/S2 for case series, functional data, phenotype literature
3. Synthesize with both in context — the model has facts to anchor on, not just training memory

**Limitations:** N=1 (genomics VUS query), single model (Sonnet). The routing may differ for other domains. Websearch may outperform academic on fast-moving fields (AI, markets) where S2 indexing lags.

## Academic Tool Selection

| Need | Best tool | Why not others |
|------|-----------|---------------|
| Canonical papers by topic | `search_papers` (S2) | Largest index (220M+), structured metadata, citation counts |
| Recent papers (<6mo) | `web_search_advanced_exa` with `category: "research paper"` + date filter | S2 has no date filtering |
| Citation analysis / related papers | `traverse_citations` (S2 graph, one hop) | Overlap filtering for multi-seed; auto-saves to corpus |
| Citation stance (support/contrast) | `search_literature` (scite) | 1.6B+ classified citations. Unique: tells you if papers *support* or *contrast* a claim |
| Disconfirmation search | `search_literature` (scite) with contrasting focus | Directly surfaces contradictory evidence — better than "X criticism" keyword hacks |
| Preprints (arXiv) | `search_arxiv` (paper-search) | Direct arXiv API, download+read built in |
| Clinical/medical literature | `search_pubmed` (paper-search) | MeSH terms, clinical focus |
| Biology preprints | `search_biorxiv` (paper-search) | Direct bioRxiv API |
| Full-text synthesis | `search_papers` → `save_paper` → `fetch_paper` → `ask_papers` | Gemini 1M context for multi-paper Q&A |
| Grey literature / expert blogs | Exa semantic search | Academic APIs don't index blogs/substacks |

## Scite — citation stance search (user-scope, available everywhere)

Scite indexes 1.6B+ citation statements classified as **supporting**, **contrasting**, or **mentioning**. Unique capability — no other tool tells you the *direction* of how papers cite each other.

- **Disconfirmation (Phase 4):** Search for contrasting citations on your hypothesis. Scite surfaces papers that explicitly contradict a claim — more targeted than keyword-based "X criticism" queries.
- **Literature audits:** Check if a specific claim has been supported or contested across the literature.
- **Novelty checks:** Before writing a claim, check if it's already in the literature and which direction the evidence points.
- **Coverage caveat:** Skews biomedical. Thin on psychometrics, measurement invariance, some social sciences.
- **Not for:** paper discovery (use S2), full-text reading (use fetch_paper), recent preprints (use arXiv/Exa).
- **Citation format:** Always check `editorialNotices` for retractions before citing. Links: `https://doi.org/{doi}`.

## Verification

- `mcp__research__verify_claim` (Exa /answer) remains primary for spot-checking.
- For critical claims: also check via `brave_web_search` (independent index).
- For citation stance: use `mcp__scite__search_literature` to check if a claim is supported or contrasted in published literature.

## Step-Level Model Routing (advisory)

| Phase | Recommended model | Rationale |
|-------|------------------|-----------|
| Phase 1-2 (explore, diverge) | Flash | Speed over depth; scanning many results |
| Phase 3-4 (hypothesis, disconfirm) | Flash | Query generation is cheap |
| Phase 5-7 (verify, synthesize) | Most capable available | Accuracy matters for final claims |
| `ask_papers` during exploration | `model="gemini-3-flash-preview"` | Don't burn Pro tokens on exploratory queries |
| `ask_papers` for final synthesis | Default (auto-selects) | Let the system pick based on corpus size |
| `prepare_evidence` | Always Flash (built-in) | Scoring is simple classification |
| `extract_table` | Always Flash (built-in) | Structured extraction is well-constrained |
