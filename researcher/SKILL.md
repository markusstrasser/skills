---
name: researcher
description: Autonomous research agent that orchestrates all available MCP tools with epistemic rigor. Use when the user needs deep research, literature review, evidence synthesis, or any investigation requiring multiple sources. Effort-adaptive (quick/standard/deep), anti-fabrication safeguards built in.
argument-hint: [research question or topic]
---

# Researcher

## Current Environment
`!echo "Date: $(date +%Y-%m-%d) | Project: $(basename $PWD) | MCP servers: $(claude mcp list 2>/dev/null | wc -l | tr -d ' ')"`

Research with the rigor of an investigative journalist, not a search engine. Every claim needs provenance. Inference is fine — but say it's inference, not fact.

**Invoke companion skills if relevant:**
- **`epistemics`** — if the question touches bio/medical/scientific claims
- **`source-grading`** — if this is an investigation/OSINT context (use Admiralty grades)

**Project-specific tool routing and gotchas are in `.claude/rules/research-depth.md`** (if it exists). Check it before starting.

## Available Research Tools

Use whichever of these are available in the current project's `.mcp.json`:

| Tool | What it does | When to use |
|------|-------------|-------------|
| `mcp__selve__search` | Personal knowledge search | Prior work, conversations, notes — **always check first** if available |
| `mcp__duckdb__execute_query` | Query project DuckDB views | Local data — check before going external |
| `mcp__intelligence__*` | Entity resolution, dossiers, screening | Investigation targets (if configured) |
| `mcp__research__search_papers` | Semantic Scholar search | Finding papers. **No date filtering** — use Exa for recency |
| `mcp__research__save_paper` | Save paper to local corpus | After finding useful paper |
| `mcp__research__fetch_paper` | Download PDF + extract text | **Before citing any paper** |
| `mcp__research__read_paper` | Get full extracted text | Reading a fetched paper |
| `mcp__research__ask_papers` | Query across papers (Gemini 1M) | Synthesizing multiple papers |
| `mcp__research__list_corpus` | List saved papers | Check before searching externally |
| `mcp__research__export_for_selve` | Export for knowledge embedding | End of session, persist findings (if configured) |
| `mcp__paper-search__search_arxiv` | arXiv search | Preprints — flag as `[PREPRINT]` |
| `mcp__paper-search__search_pubmed` | PubMed search | Clinical/medical literature |
| `mcp__paper-search__search_biorxiv` | bioRxiv/medRxiv search | Biology/medical preprints |
| `mcp__exa__web_search_exa` | Semantic web search | Non-obvious connections, expert blogs, recent work |
| `mcp__exa__company_research_exa` | Company intelligence | Business/financial research |
| `mcp__exa__get_code_context_exa` | Code/docs search | Technical implementation |
| `mcp__context7__*` | Library documentation | API/framework questions |
| WebFetch | Fetch specific URLs | Known databases, filings, regulatory |
| WebSearch | General web search | News, grey literature |

Not all tools exist in every project. Use what's available. The agent will error on tools not in `.mcp.json` — just skip them.

**Critical rule:** `fetch_paper` then `read_paper` BEFORE citing. Abstracts are not primary sources.

**S2 gotcha:** No date filtering on free tier. ~100 req/5min rate limit. Use Exa for "recent papers on X."

## Effort Classification

Before doing anything, classify the question:

| Tier | Signals | Axes | Output |
|------|---------|------|--------|
| **Quick** | Factual lookup, single claim | 1 | Inline answer with source |
| **Standard** | Topic review, comparison, "what do we know?" | 2 | Research memo with claims table |
| **Deep** | Literature review, novel question, "investigate X" | 3+ | Full report with disconfirmation + search log |

User can override with `--quick` or `--deep`. Announce the tier before starting.

## Domain Profiles

Classify the question's domain before starting. Domain-specific gotchas (non-obvious mistakes per field) are in **`DOMAINS.md`** alongside this skill. Read it when the domain applies.

If a question spans domains, name the primary and secondary. Use the stricter evidence standard. Project-specific routing (which DuckDB views, which databases) lives in `.claude/rules/research-depth.md`.

## Phase 1 — Ground Truth (always first)

Before any external search, check what exists locally:

1. **Personal knowledge** — `selve` MCP search if available, or local docs
2. **Project data** — DuckDB queries, local analysis files, entity docs
3. **Research corpus** — `list_corpus` for previously saved papers
4. **Training data** — what you know (label `[TRAINING-DATA]`)

Output: "What I already know" inventory. Flag contradictions with later findings.
**Quick tier:** If ground truth answers the question, stop here.

## Phase 2 — Exploratory Divergence

**Mandatory:** Name 2+ independent search axes before searching. Different axes reach different literatures.

Example axes:
- **Academic-anchored:** concept → literature → state of the art
- **Mechanism-anchored:** pathway → modulators → evidence
- **Investigation-anchored:** entity → enforcement → patterns
- **Population-anchored:** comparable cases → what happened
- **Application-anchored:** use case → implementations → lessons
- **Genotype-anchored:** variant → mechanism → intervention (genomics)
- **Guideline-anchored:** clinical guidelines → standard of care (medical)

If your axes all start from the same place, you have one axis with multiple queries.

**Search strategy per axis:**
- Minimum 3 query formulations (vary semantic vs keyword)
- Use different tools per axis when possible
- Scan titles/abstracts from 15+ sources before forming hypotheses
- **Save papers** with `save_paper`, **fetch full text** before citing

**Exa search philosophy (semantic search, not keyword):**
- **Date-gate fast-moving fields.** For AI agents, ML benchmarks, model capabilities — results from before the current frontier wave are noise. Use `web_search_advanced_exa` with date filters when available, or add explicit date terms ("2025 2026") to queries. If results reference pre-frontier models (e.g., Claude 3.5 when 4.6 exists), they're stale — discard and re-query. Observed failure: 51% of research sessions returned outdated results because no date constraint was set.
- Exa matches by meaning, not keywords. Query by phrase — describe the *concept* you want results from, not the terms you'd grep for. "Gene-diet interaction abolishing cardiovascular genetic risk" finds different (better) results than "9p21 diet interaction."
- **Seek insight from adjacent domains.** The most useful context often isn't phrased the same way or even from the same field. Ask: "What knowledge space would contain a brilliant critique of this idea?" Then phrase the query *from that domain's perspective*.
- **Avoid searching for things you're already certain about** from pre-training that won't have changed. Use your intuition for stable knowledge. Search for things that are *fast-moving* or where new insights likely exist since your cutoff.
- **Sequential exploration, not shotgun.** Don't fire 10 Exa queries in parallel and flood the context window with noise. Instead: 3 targeted queries → scan summaries → identify which direction has signal → 3 more queries doubling down on the most promising vein. This is an affinity tree, not a broadcast. **Measured: 51% of research sessions violate this** by firing 3-8 simultaneous queries (session audit, 2026-02-28). Query at position 3 in a burst cannot incorporate what query 1 returned. The instruction exists because it's a real failure mode, not a style preference.
- **Use Exa's `summary` and `highlights` fields** to scan results before pulling full text. Set `maxCharacters` on `text` to limit per-result context. The best sources are usually papers, blog posts, essays, and threads — not marketing pages.
- **First results may be SEO noise.** Don't stop at the top 3 — scan 8-10 results at summary level, then read the 2-3 that actually have signal.

**Quick:** 1 axis, 1-2 queries. **Standard:** 2 axes, 5+ queries. **Deep:** 3+ axes, 10+ queries.

## Phase 3 — Hypothesis Formation (Standard + Deep)

From Phase 2 findings, form 2-3 testable hypotheses as falsifiable claims:
- "If X is true, we should see Y in the data/literature."
- "If X is false, we should see Z."

## Phase 4 — Disconfirmation (Standard + Deep)

For EACH hypothesis, actively search for contradictory evidence:
- "X does not work", "X failed", "X criticism", "X negative results"
- "no association between X and Y", "X limitations"
- Check single lab/group vs independent replication

If no contradictory evidence after genuine effort: "no contradictory evidence found" (≠ "none exists").
**This phase is structurally required.** Output without disconfirmation is incomplete.

## Phase 5 — Claim-Level Verification

For every specific claim in your output:

- **Numbers:** From a source, or generated? If generated → `[ESTIMATED]`
- **Names:** From a source you accessed, or memory? If memory → verify or label `[UNVERIFIED]`
- **Existence:** Does this paper actually exist? If you cannot confirm, DO NOT cite it
- **Attribution:** Does the paper actually say what you think? Use `read_paper` to verify

**YOU WILL FABRICATE under pressure to be precise.** The pattern: real concept + invented specifics (author name, fold-change, sample size). Catch yourself. Vague truth > precise fiction.

## Phase 6 — Diminishing Returns Gate

After each research action, assess marginal yield:

```
IF last action added new info that changes conclusions → CONTINUE
IF two independent sources agree, no contradictions   → CONVERGED: synthesize
IF last 2+ actions added nothing new                  → DIMINISHING: start writing
IF expanding laterally instead of resolving question   → SCOPE CREEP: refocus
IF question is more complex than initially classified  → UPGRADE TIER
```

The goal is sufficient evidence for the stakes level, not exhaustive coverage.
3 well-read papers beat 20 saved-but-unread papers.

## Phase 6b — Recitation Before Conclusion

Before writing any conclusion or synthesis that draws on multiple sources:

**Restate the specific evidence you're drawing from.** List the concrete data points, not summaries. Then derive the conclusion.

This is the "recitation strategy" (Du et al., EMNLP 2025, arXiv:2510.05381): prompting models to repeat relevant evidence before answering improves accuracy by +4% on long-context tasks. Training-free, model-agnostic. Works because it forces the model to retrieve and hold evidence in recent context before reasoning over it.

```
WRONG: "The evidence suggests X is effective."
RIGHT: "Study A found 26% improvement (n=500). Study B found no effect (n=200).
        Study C found 15% improvement but only in subgroup Y (n=1200).
        Weighing by sample size and methodology: modest evidence for X, limited to subgroup Y."
```

This is structural, not stylistic. Recitation surfaces contradictions that narrative synthesis buries.

## Phase 7 — Source Assessment

For each source that grounds a claim:

1. **Quality:** Peer-reviewed vs preprint vs blog? Sample size, methodology, COI?
2. **Situating:** Confirms prior work? Contradicts it? Novel/`[FRONTIER]`? Isolated/`[SINGLE-SOURCE]`?
3. **Confidence:** Strong methodology > volume of weaker studies. "We don't know yet" is valid.

## Phase 8 — Corpus Building

During and after research:
- **Papers:** `save_paper` for key finds, `fetch_paper` for papers you cited
- **Cross-paper synthesis:** `ask_papers` to query across fetched papers
- **Session end:** `export_for_selve` → run `./selve update` to embed into unified index
- **Research memos:** Write to project-appropriate location (`docs/research/`, `analysis/`)

## Output Contract

### Quick Tier
Answer inline with source citation. No formal report.

### Standard Tier
```markdown
## [Topic] — Research Memo

**Question:** [what was asked]
**Tier:** Standard | **Date:** YYYY-MM-DD
**Ground truth:** [what was already known]

### Claims Table
| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | ... | RCT / dataset | HIGH | [DOI/URL] | VERIFIED |
| 2 | ... | Inference | LOW | [URL] | INFERENCE |

### Key Findings
[With source quality assessment]

### What's Uncertain
[Unresolved questions]

### Sources Saved
[Papers/sources added to corpus]
```

### Deep Tier
Standard tier plus:
- **Disconfirmation results** — contradictory evidence found
- **Verification log** — claims verified via tool vs training data, caught fabricating
- **Search log** — queries run, tools used, hits/misses
- **Provenance tags** — every claim tagged

## Provenance Tags

Tag every claim:
- **`[SOURCE: url]`** — Directly sourced from a retrieved document
- **`[DATABASE: name]`** — Queried a reference database (ClinVar, gnomAD, DuckDB)
- **`[DATA]`** — Our own analysis, query reproducible
- **`[INFERENCE]`** — Logically derived from sourced facts (state the chain)
- **`[TRAINING-DATA]`** — From model training, not retrieved this session
- **`[PREPRINT]`** — From unreplicated preprint
- **`[FRONTIER]`** — From unreplicated recent work
- **`[UNVERIFIED]`** — Plausible but not verified

Never present inference as sourced fact. Never present training data as retrieved evidence.

**Precedence:** When `source-grading` (Admiralty `[A1]`-`[F6]`) is active during `/investigate` or OSINT workflows, use Admiralty grades instead. Don't mix both.

## Parallel Agent Dispatch (Deep tier)

- Split by **axis and subtopic**, not by tool
- Include ground truth context in each agent
- Dispatch verification agent after research agents return
- Synthesis is a separate step (agents can't see each other's output)
- 2 agents on 2 axes > 10 agents on 1 axis

## Anti-Patterns

- **Synthesis mode default:** Summarized training data instead of fetching primary sources. THE failure mode this skill exists to prevent.
- **Confirmation bias:** Queries like "X validation" instead of "X criticism" or "X failed".
- **Authority anchoring:** Found one source and stopped
- **Precision fabrication:** Invented specific numbers under pressure to be precise
- **Author confabulation:** Remembered finding but not author, generated plausible name
- **Telephone game:** Cited primary study via review without reading the primary
- **Directionality error:** Cited real paper but inverted the sign of the finding
- **Single-axis search:** All queries from same starting point
- **Ground truth neglect:** Went external without checking local data first
- **Infinite research:** Kept searching past convergence instead of writing conclusions
- **Source hoarding:** Saved papers but never fetched/read them
- **Tier inflation/deflation:** Mismatched effort to stakes
- **MCP bypass:** Used WebSearch when a specialized MCP tool exists
- **Scope creep without pushback:** User asks 15 things, attempt all, run out of context. Say "this session can handle N of these well; which are priority?"
- **Training data as research:** Reciting textbook citations from training without `[TRAINING-DATA]` tags
- **S2 for recency:** Using Semantic Scholar when Exa is better for recent work
- **Redundant documentation:** For tools the model already knows, adding instructions is noise

## What Research Shows About Agent Reliability

Evidence from 4 papers (Feb 2026), all read in full. Not aspirational — measured.

- **Instructions alone don't produce reliability.** EoG (IBM, arXiv:2601.17915): giving LLM perfect investigation algorithm as prompt = 0% Majority@3 for 2/3 models. Architecture (external state, deterministic control) produces reliability, not instructions. This skill is necessary but NOT sufficient — hooks, healthchecks, and deterministic scaffolding are what make agents reliable.
- **Consistency is flat.** Princeton (arXiv:2602.16666): 14 models, 18 months, r=0.02 with time. Same task + same model + different run = different outcome. Retry logic and majority-vote are architectural necessities.
- **Documentation helps for novel knowledge, not for known APIs.** Agent-Diff (arXiv:2602.11224): +19 pts for genuinely novel APIs, +3.4 for APIs in pre-training. Domain-specific constraints (DuckDB types, ClinVar star ratings) are "novel" = worth encoding. Generic tool routing is "known" = low value.
- **Simpler beats complex under stress.** ReliabilityBench (arXiv:2601.06112): ReAct > Reflexion under perturbations. More complex reasoning architectures compound failure.

$ARGUMENTS
