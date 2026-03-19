# Search Philosophy & Strategies

Detailed search strategies, Exa philosophy, and evidence base. Loaded on demand from SKILL.md.

## Exa Search Philosophy (semantic search, not keyword)

- **Use `type: "deep"` on `web_search_advanced_exa` for high-value queries.** Deep search auto-expands your query into parallel sub-searches, ranks + merges results, and generates per-result summaries. 3x cost ($0.015/req vs $0.005 neural) but saves downstream LLM calls. Two power features:
  - **`outputSchema`** — pass a JSON Schema and get structured extraction with per-field grounding (citations + confidence: low/medium/high). Use for entity enrichment: company details, people profiles, financial data, variant annotations. Eliminates the search→fetch→extract-with-LLM chain.
  - **`additionalQueries`** — supply 2-3 domain-specific query variations. Your domain knowledge (genomics terminology, financial filing types, specific gene names) produces better variations than Exa's auto-expansion. Always generate these when you have domain context.

  Example: researching a company's financials:
  ```
  query: "Acme Corp 2025 annual revenue guidance"
  type: "deep"
  additionalQueries: ["Acme Corp 10-K SEC filing 2025", "Acme Corp Q4 earnings call transcript"]
  outputSchema: {"type": "object", "properties": {"revenue": {"type": "string"}, "guidance": {"type": "string"}, "source": {"type": "string"}}, "required": ["revenue"]}
  ```

  When NOT to use deep: simple factual lookups (use `type: "auto"`), high-throughput batch queries, when you need >100 results.

- **Use category filters on `web_search_advanced_exa`** when the domain is clear. Categories narrow results to high-signal sources:
  - `financial report` — SEC filings, earnings, annual reports (investing/finance)
  - `research paper` — academic papers (supplements S2, better recency filtering)
  - `news` — press releases, regulatory announcements, current events
  - `company` — company profiles, about pages
- **Use `highlights`** to scan results before pulling full text. Set `highlightsQuery` to your claim/topic for relevance-ranked excerpts. Useful for evidence scanning across many results.
- **Use `summary` with `summaryQuery`** for structured extraction from search results. Example: search "Company X recent earnings" with `enableSummary: true, summaryQuery: "revenue, EPS, guidance"`.
- **Match recency filter to field velocity.** Before searching, judge how fast the field moves and filter accordingly. Stable fields (physics, law) need no date gate. Fast fields (AI, crypto, geopolitics) go stale in months — if results reference superseded models, outdated benchmarks, or pre-current-generation tools, discard and re-query with tighter dates. Use `web_search_advanced_exa` `startCrawlDate`/`startPublishedDate`:
  - **Fast (AI, markets):** `startCrawlDate` = 30 days ago
  - **Medium (biotech, policy):** `startCrawlDate` = 6 months ago
  - **Stable (physics, law, math):** omit date filter
- Exa matches by meaning, not keywords. Query by phrase — describe the *concept* you want results from, not the terms you'd grep for. "Gene-diet interaction abolishing cardiovascular genetic risk" finds different (better) results than "9p21 diet interaction."
- **Seek insight from adjacent domains.** The most useful context often isn't phrased the same way or even from the same field. Ask: "What knowledge space would contain a brilliant critique of this idea?" Then phrase the query *from that domain's perspective*.
- **Know when to use your own knowledge vs. search.** Your training data is a massive library with a hard expiration date. Use it deliberately:
  - **Trust pre-training for:** foundational concepts, mathematical relationships, well-established science, historical facts, stable APIs, canonical papers (the *existence* and *core claims* of Shannon 1948 won't change).
  - **Verify via search for:** numbers that update (market caps, benchmarks, model rankings, statistics), claims about what's "state of the art," anything where the landscape shifted since your cutoff, named entities' current status.
  - **Assume stale for:** model comparisons, leaderboard positions, library versions, company valuations, anything where "latest" or "best" matters. Your training snapshot is months old — in fast fields that's a different era.
  - **Always tag it:** use `[TRAINING-DATA]` when relying on pre-training knowledge so the reader knows the provenance. This isn't a formality — it's how you distinguish "I retrieved this" from "I remember this."
  - **The dangerous zone:** you *feel* confident about a specific number, author name, or benchmark result from training. That feeling is the fabrication trigger. The more specific and numeric a memory feels, the more likely it's reconstructed, not recalled. Verify or hedge.
- **Sequential exploration, not shotgun.** Don't fire 10 Exa queries in parallel and flood the context window with noise. Instead: 3 targeted queries → scan summaries → identify which direction has signal → 3 more queries doubling down on the most promising vein. This is an affinity tree, not a broadcast. **Measured: 51% of research sessions violate this** by firing 3-8 simultaneous queries (session audit, 2026-02-28). Query at position 3 in a burst cannot incorporate what query 1 returned. The instruction exists because it's a real failure mode, not a style preference.
- **Use Exa's `summary` and `highlights` fields** to scan results before pulling full text. Set `maxCharacters` on `text` to limit per-result context. The best sources are usually papers, blog posts, essays, and threads — not marketing pages.
- **First results may be SEO noise.** Don't stop at the top 3 — scan 8-10 results at summary level, then read the 2-3 that actually have signal.

## Evidence Base: Agent Reliability Research

Evidence from 4 papers (Feb 2026), all read in full. Not aspirational — measured.

- **Instructions alone don't produce reliability.** EoG (IBM, arXiv:2601.17915): giving LLM perfect investigation algorithm as prompt = 0% Majority@3 for 2/3 models. Architecture (external state, deterministic control) produces reliability, not instructions. This skill is necessary but NOT sufficient — hooks, healthchecks, and deterministic scaffolding are what make agents reliable.
- **Consistency is flat.** Princeton (arXiv:2602.16666): 14 models, 18 months, r=0.02 with time. Same task + same model + different run = different outcome. Retry logic and majority-vote are architectural necessities.
- **Documentation helps for novel knowledge, not for known APIs.** Agent-Diff (arXiv:2602.11224): +19 pts for genuinely novel APIs, +3.4 for APIs in pre-training. Domain-specific constraints (DuckDB types, ClinVar star ratings) are "novel" = worth encoding. Generic tool routing is "known" = low value.
- **Simpler beats complex under stress.** ReliabilityBench (arXiv:2601.06112): ReAct > Reflexion under perturbations. More complex reasoning architectures compound failure.
