---
name: research
description: "Use when: 'find papers about', 'what does the latest guidance say', 'research X', 'what's known about'. One-shot research with source grading. For cycle/compile/diff/dispatch use /research-ops."
user-invocable: true
argument-hint: '[question]'
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent, WebSearch, WebFetch]
effort: high
---

# Research

One-shot research with source grading. For autonomous cycles, knowledge compilation, training-data diff, or parallel dispatch, use `/research-ops`.

## Query

## Current Environment
`!echo "Date: $(date +%Y-%m-%d) | Project: $(basename $PWD) | MCP servers: $(claude mcp list 2>/dev/null | wc -l | tr -d ' ')"`

Research with the rigor of an investigative journalist, not a search engine. Every claim needs provenance. Inference is fine — but say it's inference, not fact.

**This skill produces a research memo, not code.** If findings imply something should be built, write the memo with your findings, then offer a plan. Do not pivot to implementation within a researcher session.

**Plan persistence:** If research produces an actionable plan, write it to `.claude/plans/` or `docs/` — not just in-context. In-context plans are lost on compaction (285 lost `update_plan` calls observed in Codex sessions).

**Session awareness:** `!cat ~/.claude/active-agents.json 2>/dev/null | python3 -c "import sys,json,time; entries=json.load(sys.stdin); active=[e for e in entries if time.time()-e.get('started_at',0)<7200]; print(f'{len(active)} active sessions') if len(active)>=3 else None" 2>/dev/null`
If 3+ sessions active: keep questions shorter, batch ambiguous items.

**Companion skills:** `epistemics` for bio/medical/scientific claims. `source-grading` for investigation/OSINT (Admiralty grades).
**Project routing:** Check `.claude/rules/research-depth.md` if it exists.
**Domain gotchas:** Read `${CLAUDE_SKILL_DIR}/DOMAINS.md` when the domain applies.
**No arguments?** If invoked without a question, check `schemas/open_questions.md` or `.claude/rules/research-depth.md` for open research items, or ask the user.

## Tool Routing

**Quick routing by need:**
- **Factual lookup (need the number):** `perplexity_ask` (~$0.01-0.05/call) — returns exact figures with CIs, assembly versions, study-level breakdowns. Best when you need precise values, not just confirmation. Empirically outperformed Exa `/answer` 5-0 on genomics factual questions (exact bp counts, odds ratios, gene counts, protein sizes).
- **Factual verification (have the number, need to check it):** `verify_claim` (Exa /answer, ~$0.005/call, cached 7d) — confirms or denies a specific claim. Cheaper but less precise — says "supported" without giving the exact value. Best for checking numbers you already have.
- **Academic papers:** `search_papers` (S2, 220M+) for discovery -> `fetch_paper` + `read_paper` before citing
- **Recent papers (<6mo):** `web_search_advanced_exa` with `category: "research paper"` + date filter (S2 has no date filtering)
- **Recent preprints:** `search_preprints` (bioRxiv/medRxiv, free, date-range filtering)
- **Citation stance:** `search_literature` (scite) — 1.6B+ citations classified as supporting/contrasting/mentioning
- **Entity enrichment:** `web_search_advanced_exa` with `type: "deep"` + `outputSchema` — structured JSON with per-field citations, eliminates search->fetch->extract chains
- **Database lookups (UniProt, gnomAD, ClinVar):** Exa/Brave websearch, NOT S2 (returns papers *about* databases, not the data). This is an empirical finding (EBF3 benchmark) — websearch found exact domain boundaries that academic tools missed.
- **News/events:** `brave_news_search` (24h-7d), Exa with date filter for older
- **URL discovery / cheap search:** `perplexity_search` (~$0.005/call) — raw ranked results without AI synthesis. Comparable to Brave.
- **Triangulation:** Exa + Brave (confirmed independent indexes). Perplexity is NOT independent (uses same underlying indexes).
- **Deep "why" analysis:** `perplexity_reason` (~$0.05-0.15/call) — chain-of-thought with web grounding. Only for analytical questions needing reasoning + evidence.
- **Comprehensive surveys:** `perplexity_research` (~$0.15-0.50/call, slow 30s+) — multi-source deep research. Reserve for literature-survey-scale questions.
- **Autonomous deep research:** `deep_research` (~$2-5/call, 2-10min async) — Gemini Deep Research agent conducts 80-160 web searches autonomously. Use when the question is broad/unknown-scope, needs multi-source synthesis, and you have time. Returns a full report with inline citations. Overkill for focused questions — use the paper pipeline or perplexity_research instead.
- **Complex multi-step web research:** `parallel_task` (core ~$0.05/call, ultra ~$0.30-$2.40/call) — Parallel Task API. Code-execution sandbox keeps intermediate data out of context. Best for causal-chain questions requiring cross-referencing across multiple web sources (e.g., "find co-authors across 3 institutions, then check which joined a federal committee"). Processor tiers: lite ($0.005) for simple lookups, core ($0.05) default, ultra+ ($0.30-$2.40) for hard multi-step. 70-82% on DeepSearchQA (vs GPT-5.4 63%, Opus 58%). Latency: 10-60s. Use `parallel_search` for quick web-grounded lookups as alternative to `verify_claim`.

**Interpret Parallel benchmarks correctly:**
- Parallel's published wins are on **DeepSearchQA-style multi-hop answer generation**, not exact-source retrieval. High benchmark accuracy means the harness is good at navigating causal chains, not that it will beat Exa at landing on the single best paper/page for a memo.
- Treat `parallel_task` as a **reasoning/synthesis engine**. Treat Exa as a **retrieval engine**. These are different jobs.
- For memo-grade work where the question is really "what is the exact paper / benchmark / official page?", start with Exa (and crawl the winning URLs) before using Parallel.
- For broad "figure out the answer across many pages" questions, Parallel may beat a naive search loop.
- `ultra` is a **background job**, not an interactive tool. Prefer async start/result for `ultra` and `ultra8x`.

**Empirical routing update (genomics eval, 2026-04-07):**
- Exa beat Parallel core on **exact source targeting** for CMRG hard-locus benchmarking, targeted long-read PGx comparison, and CHIP assay-limit papers.
- Parallel core produced decent one-shot answers, but often cited broader adjacent sources instead of the sharpest primary source.
- For "write a defensible memo with the right citations," Exa search -> crawl was better.
- For "draft me an answer with citations," Parallel core was useful.

**Paper pipeline (Standard+ academic queries) — run this, not just Exa snippets:**
`search_papers` -> `save_paper` (seed papers) -> `fetch_paper` -> `get_paper` -> `prepare_evidence` -> `ask_papers(use_rcs=True)`
This is the highest-quality evidence path. RCS scoring produces significantly better synthesis than websearch snippets (PaperQA2 ablation: p<0.001). 3 well-read papers beat 20 snippet-scanned papers.

**Critical rules:**
- `fetch_paper` then `get_paper`/`read_paper` BEFORE citing. Abstracts are not primary sources.
- Treat the `fetch_paper` quality card as part of the evidence, not optional metadata. If the card says `vetoed`, do not cite the paper as ordinary support without naming the veto.
- When citing a paper with quality metadata, surface components directly: `RCT, n=200, human, double-blind, placebo, government-funded` or `VETOED — candidate gene study`.
- Never trust PMIDs or PDB IDs from websearch without S2/database verification. Websearch confabulates citation details.
- Sequential exploration: 3 broad queries -> scan results -> 3 narrower queries refining signal. Don't shotgun — query at position 3 in a burst cannot incorporate what query 1 returned.
- Search/discovery tools are **map tools**. Primary documents, official databases, and fetched full text are **evidence tools**. Do not blur them.
- For "newest", "latest", or date-sensitive queries, state the date anchor explicitly and bias toward the last 12-18 months unless the field is known to move slowly.
- If one backend is repeatedly failing (`403`, auth block, junk results), switch early. Do not spend multiple rounds proving the same backend is unreliable.

**Full tool table:** `${CLAUDE_SKILL_DIR}/references/tool-routing.md` (optional depth).

## Search Heuristics

- **Start broad, narrow later.** First 1-2 queries per axis should be short and general (3-5 words). Agents default to overly-specific initial queries that miss relevant results. "protein folding disease" before "alpha-synuclein aggregation Lewy body mechanism." Narrow progressively based on what the broad pass surfaces.
- Exa is semantic, not keyword. Describe the *concept* — "gene-diet interaction abolishing cardiovascular risk" beats "9p21 diet interaction."
- Use `type: "deep"` + `additionalQueries` (2-3 domain-specific variations) for high-value queries.
- **Recency by field velocity:** Fast fields (AI, markets) = 30-day filter. Medium (biotech, policy) = 6 months. Stable (physics, law) = no filter. If results reference superseded tools or outdated benchmarks, tighten the date.
- **Newest-seam research:** run one broad recency pass, then narrow immediately to one seam. Repeated broad recency searches mostly generate overlap, not new evidence.
- **Training data:** Trust for foundations, verify for numbers. Tag `[TRAINING-DATA]`. **The dangerous zone:** the more specific and numeric a memory feels, the more likely it's reconstructed. Verify or hedge.
- Scan 8-10 results at summary level, then read the 2-3 with signal. First results are often SEO noise.

## Effort Classification

| Tier | Signals | Axes | Queries | Tool calls | Output |
|------|---------|------|---------|------------|--------|
| **Quick** | Factual lookup, single claim | 1 | 1-2 | 3-8 | Inline answer with source |
| **Standard** | Topic review, comparison, "what do we know?" | 2 | 5-8 | 10-20 | Research memo with claims table |
| **Deep** | Literature review, novel question, "investigate X" | 3+ | 10-15 | 20-40 | Full report + disconfirmation + search log |

User can override with `--quick` or `--deep`. Announce the tier before starting.

### Adversarial Mode (`--adversarial`)

Activated by `--adversarial` flag OR when the question asks to challenge, debunk, stress-test, or "call BS on" a field, hypothesis, intervention, or result. Always Deep tier.

**What it does differently:** Inverts the default stance. Standard research asks "what does the evidence say?" Adversarial research asks "what's the strongest case that this is wrong, noise, or built on sand?" — then evaluates whether that case holds.

**Reference:** `~/Projects/agent-infra/research/adversarial-case-library.md` — 45+ curated exemplars of strong adversarial thinking across 9 domains. Read it before starting adversarial research — it has query patterns, URL sources, and quality criteria. The six markers of strong adversarial work: (1) evidence not rhetoric, (2) target genuinely believed by serious people, (3) structural not anecdotal critique, (4) often from insiders, (5) unanswered, (6) constructive null (explains what the data actually show).

**Phase modifications:**
- **Phase 1 (Ground Truth):** Inventory what the field claims and WHY people believe it. Steel-man the target before attacking.
- **Phase 2 (Search):** Mandatory axes: *replication status*, *strongest critic*, *alternative explanation*, *meta-analysis of the meta-analyses*. Creative Exa queries modeled on case library patterns — describe the concept adversarially ("the strongest case that X is noise," "someone who proved X was wrong with data," "celebrated Y finding that failed to replicate"). Use `additionalQueries` with 2-3 diverse framings per search.
- **Phase 3 (Verify):** Flip direction — verify the CRITIQUE, not the original claim. Is the debunking itself solid? Check for: overclaiming by critics, selective counter-evidence, contrarian bias.
- **Phase 4 (Synthesize):** Output is a **case brief**, not a balanced review. Structure: Target Claim -> Why It Was Believed -> The Evidence Against -> Strength of the Case Against -> What Survives -> Verdict.

**Output template (replaces standard memo):**
```markdown
## Adversarial Review: [Target]

**Target claim:** [what's being challenged]
**Prior belief:** [why serious people believed this, steel-manned]
**Date:** YYYY-MM-DD

### The Case Against
[Evidence marshaled against the target, with sources and effect sizes]

### Strength Assessment
| Criterion | Rating | Notes |
|-----------|--------|-------|
| Evidence quality | HIGH/MED/LOW | [specific] |
| Target was genuinely believed | YES/NO | [by whom] |
| Structural, not anecdotal | YES/NO | [mechanism identified?] |
| Critique is unanswered | YES/NO | [rebuttals exist?] |
| Constructive null | YES/NO | [alternative explanation?] |

### What Survives
[Parts of the original claim that withstand scrutiny]

### Verdict
[DEMOLISHED / MORTALLY WOUNDED / WEAKENED / SURVIVES WITH CAVEATS / CRITIQUE FAILS]

### Sources & Search Log
[Full provenance per standard Deep tier]
```

**Turn budget:** After exceeding your tier's tool call budget, force synthesis. Hard ceiling: 40 tool calls (Deep) or 20 (Standard). Reserve remaining capacity for writing. A partial synthesis with sources beats an exhaustive search with no output.

## Phase 0 — Dedup Check

Before starting a full research pass, check if this question was already researched recently:
`!git log --since=24h --name-only --diff-filter=A -- 'research/*.md' 'docs/research/*.md' 'artifacts/*.md' 2>/dev/null | grep -v '^$' | head -20`

If a memo on the same topic was written in the last 24 hours, read it first. If it answers the question, skip to Phase 4 (synthesize with any delta). If it partially answers, narrow your scope to the gap.

This prevents the dominant waste pattern: re-running full inventory + external search for a question that was answered hours ago.

## Phase 1 — Ground Truth

Before external search, check what exists locally:
1. **Personal knowledge** — `selve` MCP or local docs if available
2. **Project data** — DuckDB views, entity docs, local analysis
3. **Research corpus** — `list_corpus` for previously saved papers
4. **Training data** — what you know (label `[TRAINING-DATA]`)

Flag contradictions with later findings. **Quick tier:** If ground truth answers the question, stop here.

## Phase 2 — Search

**Name 2+ independent search axes before searching.** Axes must come from different categories:

| Category | Entry point | Example |
|----------|------------|---------|
| **Mechanism** | pathway -> modulators -> evidence | "How does X work?" |
| **Adversarial** | failure modes -> criticism -> limitations | "Why would X NOT work?" |
| **Adjacent domain** | analogous problem in unrelated field | "Who else solved something like X?" |
| **Historical** | prior attempts -> lessons learned | "When was X tried before?" |
| **Practitioner** | operational reality -> gotchas | "What do daily users say?" |
| **Academic** | literature -> state of the art | "What does the research say?" |
| **Population** | comparable cases -> outcomes | "Who else has X?" |

If all your axes are from the same category, you have one axis with multiple queries, not genuine diversity.

**Perspective-guided divergence (Standard+):** Choose 3-5 perspectives (practitioner, critic, adjacent-domain, historian, data analyst, regulator, end user). Generate 3-5 questions from EACH perspective — they must be genuinely different. Merge -> select 5-8 as search queries from 2+ perspective categories. This defeats the Artificial Hivemind structurally (STORM: +25% organization, +10% breadth).

**Analogical forcing (Deep, optional):** For one axis, reframe through an unrelated domain's lens — "How would a supply chain engineer think about this?" Forces different search terms and literatures.

**Search budgets:** See effort table above — queries and tool call ceilings are per-tier.

**Standard+ academic queries — run the paper pipeline:**
`search_papers` -> `save_paper` -> `fetch_paper` -> `prepare_evidence` -> `ask_papers(use_rcs=True)`

## Phase 3 — Verify

**Hypotheses (Standard+):** Form 2-3 falsifiable claims: "If X is true, we should see Y in the data/literature. If X is false, we should see Z."

**Disconfirmation (Standard+, structurally required):**
- Search for "X does not work", "X failed", "X criticism", "no association between X and Y"
- Check single lab/group vs independent replication
- If no contradictory evidence after genuine effort: "no contradictory evidence found" (not "none exists")

**Citation stance check:** For claims that assert literature consensus or direction ("evidence supports...", "studies show...", "the literature suggests..."), and for any fetched paper you plan to lean on heavily, run `search_literature` (scite) and append `[SCITE: S:X C:Y M:Z]`. These consensus claims are the highest-risk for hallucination — scite's contrasting citations catch things keyword disconfirmation misses. If scite returns 0 results, note `[SCITE: NO COVERAGE]` — don't treat absence as confirmation. (~$0/call, user-scope MCP, available everywhere.)

**Claim-level checks:**
- Numbers: from a source, or generated? If generated -> `[ESTIMATED]`
- Names/authors: from a source you accessed, or memory? If memory -> verify or `[UNVERIFIED]`
- Papers: does this actually exist? If unconfirmed, DO NOT cite it
- For high-stakes claims (valuations, statistics): use `verify_claim` (~$0.005/call)

**YOU WILL FABRICATE under pressure to be precise.** The pattern: real concept + invented specifics (author name, fold-change, sample size). Catch yourself. Vague truth > precise fiction.

## Phase 4 — Synthesize

**Stop conditions** (VMAO-derived, arxiv:2603.11445 — +35% completeness from formal verification):

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Ready for Synthesis | >=80% of search axes produced results | Write up |
| Converged | 2+ sources agree, no contradictions | Write up |
| Diminishing Returns | Last 2 actions added nothing new | Write up |
| Scope Creep | Expanding laterally, not resolving | Refocus or ask user |
| Turn Budget | 15+ search/retrieval tool calls used | Force synthesis |
| Tier Upgrade | Question more complex than classified | Upgrade tier |
| Info Changed Conclusions | Last action changed direction | Continue |

**Evaluate after every search round, not just at the end.** After each search round (2-3 queries), assess: "How many of my named search axes have produced at least one useful result? What's missing?" A "search axis" = one of the axes you named in Phase 2. "Nothing new" = the last 2 tool calls returned results already covered by existing findings.

**When to stop searching:** if the new material is collapsing into existing local concepts, the last two rounds only produce narrower restatements, or the best surviving idea is just one bounded caveat, synthesize and stop. Do not keep searching to make the output look richer.

**Recite evidence before concluding.** List concrete data points from sources, then derive the conclusion. "Study A: 26% improvement (n=500). Study B: no effect (n=200). Weighing by sample size..." This surfaces contradictions that narrative synthesis buries.

**Refuse if evidence is insufficient.** If you have only `[TRAINING-DATA]` or `[UNVERIFIED]` tags with no retrieved sources directly addressing the question, output:
```
## Insufficient Evidence
**Question:** ... | **Searched:** ... | **Not found:** ... | **Partial findings:** ... | **Next steps:** ...
```
Confident synthesis from noise is worse than an informative refusal.

**Source assessment:** For each key source — peer-reviewed vs preprint vs blog? Sample size, methodology, COI? Confirms or contradicts prior work? "We don't know yet" is valid.

<output_contract>
## Output Contract

### Claim-Level Source Gating (Mandatory)

**Every empirical quantitative claim** (effect sizes, trial results, epidemiological numbers, "X reduces Y by Z%") in the output MUST have:
- A resolved DOI or PMID
- The specific finding from that source that supports the claim

This does NOT apply to:
- **Deductive claims** — math, inference from known quantities, logical derivation -> tag `[INFERENCE]`, valid without DOI
- **Computed values** — dose/kg from body weight, unit conversions -> tag `[DATA]`, valid
- **Established facts** — well-known biology (e.g. "CYP2D6 metabolizes codeine") -> no source needed

Empirical claims without source provenance are tagged `[UNSOURCED]`. Unsourced empirical claims should not drive protocol decisions or dosage recommendations without explicit acknowledgment of the gap.

**Paper quality assessment** (auto-runs on `fetch_paper`, returns quality card):

Hard vetoes (block citation):
- `RETRACTED` — never cite retracted papers (Crossref + PubMed fallback)
- `CANDIDATE_GENE` — pre-GWAS single-gene association studies (~98% non-replication). Exempts PGx (CYP*, HLA, UGT) and mechanism studies.

Informational flags (surface to reader, don't auto-block):
- `NON_HUMAN_ONLY` — animal/in-vitro biological study. Transfer depends on context: conserved pathways (energy metabolism, DNA repair) transfer; PK, behavior, immune do not. State the organism.
- `CASE_REPORT_ONLY` — case reports establish existence, not magnitude.
- Blinding (open-label inflates effects), control type (waitlist inflates), single-center, industry-funded, no pre-registration, data "on request" — all informational.

When citing papers with quality metadata, include component display:
"Paper X: RCT, n=200, human, double-blind, placebo, gov-funded" or "Paper Y: VETOED — candidate gene study"

Don't build composite scores or traffic lights from these components. Display them as a list. The citing agent (you) makes the judgment call based on context.

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
| 3 | ... | None found | — | — | UNSOURCED |

### Key Findings
[With source quality assessment and paper quality metadata where available]

### What's Uncertain
[Unresolved questions]
```

### Deep Tier
Standard tier plus: **Disconfirmation results**, **Verification log** (claims verified via tool vs training data), **Search log** (queries, tools, hits/misses).

## Provenance Tags

Tag every claim:
- **`[SOURCE: url]`** — Retrieved document
- **`[DATABASE: name]`** — Reference database query (ClinVar, gnomAD, DuckDB)
- **`[DATA]`** — Our own analysis, reproducible
- **`[INFERENCE]`** — Logically derived (state the chain)
- **`[TRAINING-DATA]`** — From model training, not retrieved
- **`[PREPRINT]`** / **`[FRONTIER]`** — Unreplicated work
- **`[UNVERIFIED]`** — Plausible but not verified
- **`[SCITE: S:X C:Y M:Z]`** — Citation stance from scite
- **`[ESTIMATED]`** — Number generated, not sourced

Never present inference as sourced fact. Never present training data as retrieved evidence.

**Precedence:** Admiralty grades (`[A1]`-`[F6]` per `source-grading` skill) are the standard for investigation/OSINT — strictly more granular. Don't duplicate by tagging the same claim with both systems.
</output_contract>

<anti_patterns>
## Anti-Patterns

- **Synthesis mode default:** Summarized training data instead of fetching primary sources — THE failure mode
- **Confirmation bias:** "X validation" queries instead of "X criticism" or "X failed"
- **Precision fabrication:** Invented numbers or author names under pressure to be precise
- **Telephone game:** Cited primary via review without reading the primary
- **Single-axis search:** All queries from same starting point, same intellectual tradition
- **Source hoarding:** Saved papers but never fetched/read them
- **Scope creep without pushback:** User asks 15 things — say "this session can handle N well; which are priority?"
- **Websearch citations as primary:** Trusting PMIDs/PDB IDs from websearch without S2 verification
- **Academic tools for database lookups:** Using S2 for gnomAD frequencies — query the database directly
- **Exa monoculture:** Using only Exa when S2/scite/Brave would reach different sources
- **Skipping paper pipeline:** Using Exa snippets when `search_papers` -> `fetch_paper` -> `ask_papers` would give higher-quality evidence
</anti_patterns>

$ARGUMENTS
