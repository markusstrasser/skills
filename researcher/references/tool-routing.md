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
| `mcp__exa__web_search_exa` | Semantic web search | Non-obvious connections, expert blogs, recent work |
| `mcp__exa__web_search_advanced_exa` | Advanced search (filters, deep, structured) | Entity enrichment, date-filtered research, domain-restricted search |
| `mcp__exa__company_research_exa` | Company intelligence | Business/financial research |
| `mcp__brave-search__brave_web_search` | Independent index search | Triangulation with Exa (different index) |
| `mcp__brave-search__brave_news_search` | Dedicated news search | Time-sensitive events (default 24h) |
| `mcp__perplexity__perplexity_ask` | Grounded factual answer | Quick cited answer. Saves search→fetch→synthesize. |
| `mcp__perplexity__perplexity_research` | Deep multi-source report | Comprehensive surveys. Slow (~30s+). |
| `mcp__perplexity__perplexity_reason` | Chain-of-thought + web | Analytical "why" questions needing reasoning + evidence. |
| `mcp__scite__search_literature` | Citation-stance search (1.6B+ citations) | Disconfirmation, literature audits, checking if a claim is supported/contrasted. Returns Smart Citation snippets with stance. |
| `mcp__firecrawl__firecrawl_scrape` | JS-heavy page scraper | Financial dashboards, dynamic sites. Only if configured. |
| `mcp__context7__*` | Library documentation | API/framework questions |
| WebFetch | Fetch specific URLs | Known databases, filings, regulatory |

Not all tools exist in every project. User-scope MCPs (scite, perplexity, brave-search, exa) are available everywhere. `research` MCP (papers-mcp) is per-project.

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

## Evidence Base: Agent Reliability

- **Instructions alone ≠ reliability.** EoG (IBM, arXiv:2601.17915): perfect algorithm as prompt = 0% Majority@3 for 2/3 models. Architecture produces reliability.
- **Consistency is flat.** Princeton (arXiv:2602.16666): 14 models, 18 months, r=0.02. Same task + same model + different run = different outcome.
- **Documentation helps for novel knowledge, not known APIs.** Agent-Diff (arXiv:2602.11224): +19 pts for genuinely novel APIs, +3.4 for APIs in pre-training.
- **Simpler beats complex under stress.** ReliabilityBench (arXiv:2601.06112): ReAct > Reflexion under perturbations.
