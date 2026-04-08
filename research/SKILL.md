---
name: research
description: "Discovery and synthesis — one-shot research, CORAL-epoch loops, knowledge compilation, training-data diff, parallel Codex dispatch. MCP-orchestrated with source grading."
user-invocable: true
argument-hint: <mode> [query or topic]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent, WebSearch, WebFetch]
effort: high
---

# Research

Unified research workflow with five modes. Default is `query`.

| Mode | Trigger | What it does | Origin |
|------|---------|--------------|--------|
| `query` | `/research <question>` (default) | One-shot MCP research with source grading | researcher |
| `cycle` | `/research cycle` | Autonomous discover/gap/plan/review/execute/verify loop via `/loop 15m` | research-cycle |
| `compile` | `/research compile <concept>` | Synthesize memos into unified article | knowledge-compile |
| `diff` | `/research diff <text or path>` | Extract what's NOT in training data | knowledge-diff |
| `dispatch` | `/research dispatch [depth]` | Parallel Codex CLI audit sweep | dispatch-research |

---

# Mode: query

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
`search_papers` -> `save_paper` (seed papers) -> `fetch_paper` -> `prepare_evidence` -> `ask_papers(use_rcs=True)`
This is the highest-quality evidence path. RCS scoring produces significantly better synthesis than websearch snippets (PaperQA2 ablation: p<0.001). 3 well-read papers beat 20 snippet-scanned papers.

**Critical rules:**
- `fetch_paper` then `read_paper` BEFORE citing. Abstracts are not primary sources.
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

**Reference:** `~/Projects/meta/research/adversarial-case-library.md` — 45+ curated exemplars of strong adversarial thinking across 9 domains. Read it before starting adversarial research — it has query patterns, URL sources, and quality criteria. The six markers of strong adversarial work: (1) evidence not rhetoric, (2) target genuinely believed by serious people, (3) structural not anecdotal critique, (4) often from insiders, (5) unanswered, (6) constructive null (explains what the data actually show).

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

**Citation stance check:** For claims that assert literature consensus or direction ("evidence supports...", "studies show...", "the literature suggests..."), run `search_literature` (scite) and append `[SCITE: S:X C:Y M:Z]`. These consensus claims are the highest-risk for hallucination — scite's contrasting citations catch things keyword disconfirmation misses. If scite returns 0 results, note `[SCITE: NO COVERAGE]` — don't treat absence as confirmation. (~$0/call, user-scope MCP, available everywhere.)

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

---

# Mode: cycle

You run on `/loop`. Each tick you read state, pick the next phase, and execute it — via subagent (preferred, fresh context) or inline (if memory-constrained). **Never ask for input.** The human steers by editing CYCLE.md between ticks.

## Live State

!`bash ${CLAUDE_SKILL_DIR}/scripts/gather-cycle-state.sh "$(pwd)" 2>&1 | head -80`

## Rate Limit Detection

Before each tick, check rate limit status:
```bash
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
```

**If rate-limited (CLAUDE_PROCS >= 6):** Route LLM-heavy phases (discover, gap-analyze, plan) through llmx instead of Claude subagents:
- Use `llmx chat -m gemini-3-flash-preview` for discover/gap-analyze (search + synthesis — Flash is free via CLI)
- Use `model-review.py` for review (already routes through llmx)
- Execute and verify phases use tools, not LLM reasoning — run inline regardless
- Write `[rate-limited: used llmx]` tag in CYCLE.md log entries for tracking

**If not rate-limited:** Normal operation (Claude subagents preferred).

## Each Tick

If "NO STATE CHANGE" -> one-line noop, stop.

Otherwise, pick the highest-priority phase and run it. **Chain phases** if confident — don't wait for the next tick when the next phase has no blockers. Stop chaining when: rate-limited, context is heavy (>60% used), or the next phase needs external data you don't have yet.

### Phase Priority (first match wins)

1. **Recent execution without verification** -> run verify (always verify before executing more)
2. **Items in queue** (CYCLE.md `## Queue`) -> run execute. The queue IS the approval — items land there via human steering or gap-analyze. No `[x] APPROVE` gate needed.
3. **Active plan not yet reviewed** -> run review (probe claims + cross-model via `model-review.py`)
4. **Gaps exist without plan** -> run plan phase (write plan for top gap)
5. **Discoveries exist without gap analysis** -> run gap-analyze
6. **Verification done without improve** -> run improve (includes retro + archival)
7. **Nothing pending** -> run discover (includes brainstorm if discover returns empty)

### Running a Phase

**Route by task type, not line count:**
- Docstring, config, research_only field changes -> **inline** (fast, reliable)
- Logic changes, even 1-line -> **subagent** (fresh context for reasoning about consequences)
- If subagent returns empty (no edit), retry inline once

**Subagent dispatch (normal mode):**
```
Agent(
  prompt="[phase prompt with project context]",
  subagent_type="general-purpose",
  description="research-cycle: [phase]",
  mode="bypassPermissions"
)
```

**llmx dispatch (rate-limited mode):** For discover/gap-analyze/plan phases, write the phase prompt to a temp file and dispatch via llmx:
```bash
cat > /tmp/cycle-phase-prompt.md << 'EOF'
[phase prompt with project context]
EOF
llmx chat -m gemini-3-flash-preview -f /tmp/cycle-phase-prompt.md \
  --timeout 120 -o /tmp/cycle-phase-output.md \
  "[phase instruction]"
# Read output, apply to CYCLE.md, commit
```
Gemini Flash is free via CLI transport — no rate limit conflict with Claude. For phases needing tool use (discover with Exa/S2), work inline with MCP tools but skip subagent delegation.

**Fallback priority:** subagent (fresh context) -> llmx (rate-limited) -> inline (memory-constrained + rate-limited).

Each phase prompt must include:
- Project root path and name
- Current CYCLE.md content (relevant sections only)
- "Write results back to CYCLE.md. Commit if files changed. Do NOT ask for input."
- **Turn budget:** "Stop searching at 70% of your turns and synthesize. Do NOT exhaust all turns on searching."
- **Recitation:** "Before drawing conclusions, recite the key evidence you're working with."

### Phase Prompts

**Discover:** Search for new information relevant to this project. Lead with Exa (more reliable for tools/releases), then search_preprints for papers. For deep audit sweeps, invoke `/research dispatch`. Compare against git log and research memos. Write findings to CYCLE.md `## Discoveries` as `- [NEW] ...`. Skip anything already known. Commit. Stop searching at 70% of turns and write up. **If nothing found:** invoke `/brainstorm` on the project domain inline. Write ideas to DECISIONS.md as informational context (not approval items). One phase total — brainstorm is part of discover.

**Gap-analyze:** Read CYCLE.md discoveries + improvement signals (from Live State `IMPROVEMENT SIGNALS` section) + project state (CLAUDE.md, git log, research index). Two gap sources: (1) discoveries from discover phase, (2) improvement signals — prioritize `STEER` signals (human steering load) alongside quality/reliability signals. SWE quality gaps (code bugs, freshness, refactoring) are handled by `/maintain` in the separate SWE quality lane — don't duplicate that work here. Write prioritized gaps to `## Gaps`. Classify each: autonomous (reversible, existing pattern) or needs-approval. Commit.

**Plan:** Read top gap from `## Gaps` (skip any marked `FAILED` within cooldown). **Before planning:** check `artifacts/failed-experiments/` for prior attempts on the same subsystem — if found, include "Previously tried: {plan_summary}. Failed because: {failure_reason}" in the plan context so the LLM avoids repeating the same approach. Write implementation plan to `## Active Plan`: files to change, what changes, verification method. Add to `## Queue` for execution. Commit.

**Review:** Three steps — blind assessment, probe, then cross-model review:
1. **Blind first-pass:** Read the plan WITHOUT re-reading the gap-analyze output. Form an independent assessment of whether the plan addresses the right problem and has the right approach. Write your assessment. THEN compare to the gap-analyze output and note divergences. This breaks confirmation bias (SycEval baseline: 58% fold rate without structural mitigation).
2. **Probe external claims inline:** If the plan references any URL, API endpoint, or version number, HTTP-probe it directly. This catches 404s and HTML-instead-of-API before wasting a review cycle (caught 2 bugs in 6 cycles).
3. **Cross-model review via script:** Write the plan to a temp file, then dispatch:
```bash
uv run python3 ~/Projects/skills/model-review/scripts/model-review.py \
  --context /tmp/cycle-plan.md \
  --topic "research-cycle-G{N}" \
  --axes simple \
  --project "$(pwd)" \
  "Review this plan for wrong assumptions, missing steps, and anything that could break existing functionality"
```
Route `--axes` by stakes: `simple` for autonomous/low-risk, `standard` for needs-approval, `deep` for structural changes. Skip cross-model entirely for trivial changes (docstring fixes, config tweaks).
Read the output files, apply verified findings to plan. If critical issues, move plan back to gaps. **On model-review failure:** check exit code + stderr before retrying. Classify: auth (retry), rate-limit (fall back to other model), timeout (reduce context), schema error (fix input). Do NOT blindly retry the same model (FM24). Commit.

**Execute:** Read reviewed plan. Implement it — the queue is the approval, no `[x]` gate. **Before executing:** note current HEAD SHA. After implementation, commit. **Reflect inline** (1-3 lines under the done entry): what was easier/harder than planned, did plan assumptions hold, anything to carry forward. Move item from Active Plan to `## Autonomous (done)` with date + reflection. Mark corresponding gap entry with `~~done~~` prefix.

**Verify:** Check most recent item in `## Autonomous (done)`. Two verification tracks depending on output type:

**Track A — Infrastructure changes** (code, config, hooks, scripts): Run relevant tests, check file existence, compare with known-good data. Same as before.

**Track B — Research output** (executed item produced or modified `research/*.md`): Run factual claim verification:
1. Extract 3-5 key factual claims from the output (specific numbers, dates, named entities, causal assertions — not opinions or interpretations)
2. For each claim, call `verify_claim` MCP tool
3. Record verdicts in `## Verification Results`:
   ```
   [DATE] **[item]:** claim verification (N claims checked)
   - "Claim text" -> supported (0.85) PASS
   - "Claim text" -> insufficient (0.4) WARN
   - "Claim text" -> contradicted (0.9) FAIL
   ```
4. **FAIL threshold:** Any claim "contradicted" with confidence >0.7 -> trigger revert flow below
5. **WARN threshold:** "insufficient" verdicts -> append to DECISIONS.md for human review, don't block
6. If all claims supported or insufficient with low confidence -> PASS

For both tracks, write results to `## Verification Results`. **If verification fails:**
1. **Archive the failed attempt** before reverting (DGM-H variant preservation):
   ```bash
   mkdir -p artifacts/failed-experiments
   git format-patch HEAD~1 -o artifacts/failed-experiments/
   ```
   Write a JSON sidecar `artifacts/failed-experiments/{gap-id}-{date}.json` with gap fingerprint schema: `{gap_id, repo, subsystem, failure_mode, mechanism_tags, base_commit, failing_metric, plan_summary, failure_reason, date, patch_file}`. Schema at `~/Projects/meta/schemas/gap-fingerprint.json`.
2. Run `git revert HEAD` (preserves history, unlike reset).
3. Mark the gap as `FAILED: {reason}` — skip it for 2 cycles.
4. Write failure to DECISIONS.md for human triage.
**TTL:** During improve phase archival, prune `artifacts/failed-experiments/` entries >90 days old that were never retrieved by a plan phase.

**Improve:** Three parts — retro + archival + proposals.
1. **Retro (structured):** Classify this cycle's events using retro categories: WRONG_ASSUMPTION, TOOL_MISUSE, SEARCH_WASTE, TOKEN_WASTE, BUILD_THEN_UNDO. Write structured findings to `## Cycle Retro` in CYCLE.md. Also write JSON to `~/Projects/meta/artifacts/session-retro/{date}-cycle.json` for the improvement pipeline.
2. **Archival:** Move entries older than 2 cycles from `## Autonomous (done)`, `## Verification Results`, and `## Cycle Retro` to `CYCLE-archive.md`. Keep CYCLE.md under 200 lines.
3. **Proposals:** Write tool/process improvement proposals to `## Tool Improvements (proposed)`. For structural improvements, write to `~/.claude/steward-proposals/`. For things needing human input, append to `DECISIONS.md` (informational — no approval checkboxes). NEVER implement tool changes directly — propose only. Commit.

### Queue Management

- **The queue IS the approval.** Items in `## Queue` are ready to execute. No `[x] APPROVE` mechanism — the human steers by adding/removing/reordering items in the queue between ticks.
- Human removes items from queue to block them. Human adds items to queue to request them.
- **Auto-defer:** Queue items that fail execution twice auto-move to `## Deferred` with failure reason.

### WIP Caps

- Max 3 undispositioned discoveries
- Max 1 active plan
- Discovery skips if 3+ undispositioned discoveries exist

### Autonomy Boundary

- **Autonomous (most things):** refactoring, architecture, integration, infrastructure, database refreshes, config tweaks, `research_only` additions, new scripts, test runs, verification, removing dead code, consolidating duplicates, wiring new stages. Given enough context, the model outperforms the human on how-to-build decisions.
- **Human steers what-to-build:** which analyses matter personally, which clinical decisions to encode, GOALS.md direction. The human expresses this by editing CYCLE.md queue between ticks.
- **Never autonomous:** changing classification thresholds with clinical implications, modifying validated clinical logic, deploying new verification tools (propose only — recursive hallucination trap)

### Human Steering via CYCLE.md

The human edits CYCLE.md between ticks:
- Add items to `## Queue` to request work
- Remove items from `## Queue` to block them
- Delete discoveries or gaps to dismiss them
- Add notes under gaps to redirect approach
- Add `## Priority: ...` to override phase selection

The skill reads CYCLE.md fresh each tick. Human edits take effect on the next tick.

## Shared Files (coordination with human)

| File | Owner | Others | Purpose |
|------|-------|--------|---------|
| `CYCLE.md` | research-cycle | human steers | Growth state + approval queue |
| `CYCLE-archive.md` | research-cycle (improve phase) | human reads | Completed items, old retros |
| `DECISIONS.md` | any skill appends | human reads | Informational: questions, ideas, proposals. NO approval checkboxes. |

Note: `/maintain` owns the separate SWE quality lane (`MAINTAIN.md`). research-cycle does not read or write maintenance state.

**DECISIONS.md convention** (append-only, informational — no approvals here):
```markdown
### [skill-name] Title (date)
Context, question, or idea for human consideration.
No [x] checkboxes — approvals go to CYCLE.md ## Queue only.
```

## Skill Invocations

| Situation | Invoke | Why |
|-----------|--------|-----|
| Deep audit sweep (SWE quality) | `/improve maintain` owns this lane | Use `/research dispatch` directly for growth-adjacent audits only |
| Plan review (non-trivial) | `/review model` via script | Cross-model adversarial — same-model can't catch own blind spots |
| Discover returns empty | `/brainstorm` inline | Divergent ideation -> ideas to DECISIONS.md (informational) |
| Need literature depth on a paper | `/research query` | Deep paper analysis with epistemic rigor |
| Improve phase (every cycle) | retro classification framework | Structured findings -> JSON for improvement pipeline |
| Domain claim verification | `/bio-verify` or biomedical MCP | Tool-backed evidence, not model reasoning |
| External tool/version check | `/trending-scout` (meta only) | Agent ecosystem scans — not for domain projects |

## Error Recovery

If any phase fails with an error (script crash, tool denied, MCP timeout):
1. Log the error to CYCLE.md `## Errors`
2. Skip the phase for this tick
3. Don't retry the same failing phase more than once consecutively
4. Write the error to DECISIONS.md for human triage
5. Continue to the next tick

## Instrumentation (append to MAINTENANCE.log each improve phase)

Log these counters for measurement:
- `orphan_rate`: approved items not acted on within 2 ticks
- `duplicate_rate`: same discovery/gap appearing twice
- `swe_lane_items`: items in MAINTAIN.md (tracked by /maintain, not research-cycle)
- `review_catch_rate`: issues caught in review
- `verify_fail_rate`: execute -> verify failures
- `cycle_latency`: ticks from discovery to shipped item

## Operating Rules

1. **Never ask for input.** Write questions to DECISIONS.md (informational) and move on.
2. **Chain confidently, stop when blocked.** Run multiple phases in one tick if the next phase has no external blockers. Stop when: rate-limited, context heavy (>60%), waiting on external data/downloads, or hit a "never autonomous" boundary.
3. **Report in 1-3 lines.** Phase run, outcome, what's next. No preamble.
4. **Budget awareness.** Track cumulative cost in CYCLE.md header. Warn at $15/day.
5. **Idempotent.** Check git log and CYCLE.md before acting. Don't redo completed work.
6. **Verify before execute.** Never start a new execution with an unverified prior change.

---

# Mode: compile

Synthesize scattered research memos into a unified concept article for **human consumption**. Reads across projects, extracts claims with provenance, surfaces contradictions, identifies gaps.

**This is a human UX tool, not an agent navigation tool.** Evidence shows agents navigate better with flat source files + grep than with pre-synthesized articles (Cao et al. 2026: retrieval hurts by 40.5%; Gloaguen et al. 2026: broad context files reduce agent success by 0.5-3% and inflate cost by >20%). Compiled articles are for the human to read when they want a consolidated view of cross-project knowledge. Do NOT build a systematic "wiki layer" of compiled articles — agents should grep the source memos directly.

**Not an entity page.** Entity pages (via /entity-management) track facts about a single entity with versioned provenance. Compiled articles synthesize *understanding* across multiple sources and multiple entities.

## When to Use

- **Human** asks "what do we know about X across projects?" and wants a readable overview
- Before a **human decision** that depends on cross-project domain knowledge
- After a research cycle, to help the **human** consolidate understanding
- Multiple research memos (3+) touch the same concept but were written in different sessions/projects and haven't been synthesized

## Phases

### Phase 1: Discover Sources

Search across all three projects for the concept:

```bash
# Header-grep FIRST — finds files where concept is a primary topic
grep -r "^#.*{concept}" ~/Projects/selve/docs/ ~/Projects/genomics/docs/ ~/Projects/meta/research/ --include="*.md" -l

# MCP search for section-level matches
search_meta("{concept}", scope="all", max_tokens=500)
```

List all matching files with a one-line relevance snippet. Discard files that mention the concept only in passing (single reference in a list). Keep files where the concept is a primary topic or has a dedicated section.

**Stop at 70% of turns and synthesize** — don't search exhaustively.

### Phase 2: Read and Extract

For each source file (up to 15):

1. Read the file (or relevant sections if large)
2. Extract discrete claims about the concept, each with:
   - The claim text
   - Source file path and project
   - Date (from frontmatter or filename)
   - Confidence/conviction level (if stated)
   - Source grade (if tagged, e.g., [A1], [CALC])
3. Note any contradictions between sources
4. Note the date of each source — older claims may be superseded

### Phase 3: Compile

Produce a unified markdown article:

```markdown
---
type: compiled
concept: {Concept Name}
compiled: {YYYY-MM-DD}
sources: {N}
projects: [{list of projects with sources}]
---

## Summary

[2-3 sentence overview of current understanding. Lead with what's known,
then what's uncertain.]

## Key Claims

| # | Claim | Source | Project | Date | Grade |
|---|-------|--------|---------|------|-------|
| 1 | ... | pgx_deep_dive.md | selve | 2026-03 | [A1] |
| 2 | ... | combinatorial_pgx_memo.md | genomics | 2026-02 | [CALC] |

[Order by confidence, not chronologically. Highest-confidence claims first.]

## Contradictions and Open Questions

[Where sources disagree, cite both sides with their provenance.
These are the most valuable part — they surface disagreements that
live in different repos and would otherwise go unnoticed.]

## Timeline

[If the understanding evolved over time, show the progression:
when beliefs changed and why.]

## Cross-References

[Links to all source memos, grouped by project]

## Gaps

[What's missing — questions that no source addresses, data that
would resolve contradictions, follow-up research suggested.]
```

### Phase 4: File

Route the compiled article based on scope:

**Cross-project compilations** (sources from 2+ projects):
- Write to `~/Projects/meta/research/compiled/{concept-slug}.md`

**Single-project compilations** (all sources from one project):
- Write to that project's `docs/compiled/{concept-slug}.md`

Create the `compiled/` directory if it doesn't exist.

Commit with message: `[research] Compile {concept} — {N} sources across {projects}`

## Anti-Patterns

- **Don't compile with <3 sources.** Below 3, just read the memos directly.
- **Don't resolve contradictions.** Surface them. Resolution requires judgment the skill doesn't have.
- **Don't include every mention.** A memo that mentions CYP2D6 once in a list is not a source about CYP2D6. Filter to substantive coverage.
- **Don't skip the gaps section.** The gaps are what make the next research session productive.
- **Don't build a wiki layer.** Evidence shows pre-synthesized articles hurt agent navigation. Compile for human understanding, not for agent consumption.

---

# Mode: diff

Extract the information delta between a text and your training knowledge. The output should let a fresh model instance — with no memory of the original text — reason about the topic as if it had read it.

## Input Handling

Accept input as:
1. **Inline text** — user pastes directly after the command
2. **File path** — read the file
3. **URL** — fetch and extract (use WebFetch or firecrawl_scrape)

If no input provided, ask: "Paste the text, or give me a file path / URL."

## Calibrating Your Knowledge Boundary

Before extracting, establish what you actually know vs. don't:

**Training cutoffs (as of 2026-03):**
- Claude Opus/Sonnet 4.6: ~May 2025
- GPT-5.4: ~April 2025
- Gemini 3.1 Pro: ~March 2025

**Reliability by source date:**
- **Pre-2024:** Almost certainly in training. Self-test is unreliable here — you'll both miss things you "know" and flag things you don't. Low value unless the source is niche/private.
- **2024-cutoff:** Partially in training. Medium reliability. Flag with `[UNCERTAIN -- may be in training]` when unsure.
- **Post-cutoff:** Genuinely novel. High delta density expected. Most valuable use case.
- **Private/unpublished content:** Always novel regardless of date. Highest reliability.

**The fundamental honesty problem:** You cannot reliably introspect on your own knowledge boundaries (SimpleQA: ~72% accuracy across frontier models -- 28% of "confident" factual answers are wrong). This skill works best when the content is *obviously* outside your training (post-cutoff, private, niche domain). For borderline cases, state uncertainty rather than guessing.

**Optional verification:** If `verify_claim` is available, spot-check 2-3 extracted "novel" claims. If Exa/Brave finds them in multiple pre-cutoff sources, they're probably not novel -- you just failed to recall them. Reclassify as `[IN TRAINING -- failed to recall]`.

## The Process

### Step 1: Read and Internalize

Read the full text. Note the publication date if available — this calibrates your confidence in the self-test.

### Step 2: Self-Test

For each candidate statement, apply this filter:

> "Could I produce this claim as an answer to a direct question, WITHOUT having seen this text, purely from pre-training?"

- **Yes -> exclude.** This is already in your weights.
- **Uncertain -> include with caveat.** Tag `[UNCERTAIN]` — may be in training but you can't confirm.
- **No -> include.** This is the delta.

Edge cases:
- **Known concept, novel application:** Include. "Transformers can do X" might be novel even if you know transformers.
- **Known fact, novel framing:** Include only if the framing itself is the insight.
- **Quantitative claims with specific numbers:** Include — models confabulate exact figures even for "known" topics. Specific numbers are almost always delta.
- **Named entities you haven't seen:** Include with `[NEW ENTITY]` tag.
- **Benchmark results, version numbers, release dates:** Almost always delta — these change frequently and models hallucinate stale values.

### Step 3: Extract as Atomic Statements

Output self-contained, declarative statements. Each must:
- Be **standalone** — understandable without the source text
- Be **falsifiable** — testable, not vague
- Preserve **specificity** — keep names, numbers, dates, mechanisms
- Avoid demonstrative pronouns that reference something outside the statement

Bad: "The authors found this approach works better."
Good: "LoRA fine-tuning with rank 4 matches full fine-tuning on MMLU within 0.3% for Llama-3 70B (Hu et al., 2024)."

### Step 4: Organize by Information Type

Group the extracted statements:

```markdown
## Knowledge Diff: [source title or description]
**Source date:** [date if known, else "unknown"]  |  **Model cutoff:** [your cutoff]  |  **Confidence:** [high if post-cutoff/private, medium if near-cutoff, low if pre-cutoff]

### Novel Claims (things you likely can't produce from training)
- [statement]

### Novel Quantitative (specific numbers, dates, benchmarks)
- [statement]

### Novel Entities or Terminology
- [statement] `[NEW ENTITY]`

### Novel Relationships (known concepts, new connections)
- [statement]

### Corrections (contradicts what you'd predict from training)
- [statement] — **Contradicts:** [what you'd have said instead]
```

### Step 5: Completeness Check

If the source text had N major sections or arguments, verify each produced at least one delta statement. If a section produced zero delta, note: "Section [X]: no novel information detected — aligns with training knowledge."

### Step 6: Compression Signal

End with:

```
---
Source: [title/URL/filename]
Delta density: [low/medium/high] — [X] novel claims from ~[Y] word source
Dominant novelty type: [claims/quantitative/entities/relationships/corrections]
```

If delta density is genuinely zero (the text contains nothing beyond your training), respond with `...` and a one-line explanation of why.

## Guardrails

- **No summarizing.** This is not a summary. A summary captures the text's main points. A diff captures only what's NEW relative to your knowledge.
- **No hedging inflation.** Don't include things "just in case" you might not know them. If you're >90% confident you'd produce it from training, exclude it. But DO include with `[UNCERTAIN]` when genuinely unsure — false negatives (missing real delta) are worse than false positives.
- **No editorial commentary.** Don't evaluate whether the novel claims are correct — just extract them. The user decides what to do with the delta.
- **Preserve the author's precision.** If the source says "37.2%", don't round to "about 37%". The specificity IS the delta.
- **State the date.** Always note the source's publication date (if known) and your training cutoff in the output header.

---

# Mode: dispatch

Research -> Dispatch -> Verify -> Plan -> Execute. Opus orchestrates the full loop: dispatches parallel audits to GPT-5.4 via Codex CLI, verifies findings against actual code, synthesizes an execution plan, then implements it.

## When to use

"dispatch research", "run audits", "codex sweep", "audit and fix", or when the user wants autonomous project improvement — from discovery through implementation.

**Depth modes:**
- `"quick sweep"` -> 3-5 lightweight audits, stop at findings (no execute)
- `"audit"` / default -> full 5-phase loop
- `"deep audit"` -> 15+ thorough audits, comprehensive plan

**Stop points:** "just audit" (stop after Phase 3), "plan only" (stop after Phase 4), "full auto" (all 5 phases).

## Pipeline

```
Phase 1: RECON     Read project state, identify gaps              (~15%)
Phase 2: DISPATCH  Craft prompts, fire 3-5 parallel Codex audits  (~25%)
Phase 3: VERIFY    Check findings against actual code              (~20%)
Phase 4: PLAN      Synthesize verified findings into exec plan     (~15%)
Phase 5: EXECUTE   Implement the plan (with user approval)         (~25%)
```

## GPT-5.4 via Codex — what to know

**CAN do:** Read files, shell commands, cross-reference, count/compare, structured output. Has 9 MCPs (scite, exa, brave, perplexity, research, meta-knowledge, paper-search, context7, codex_apps).

**CANNOT do:** DB queries, `uv`/project CLIs (sandbox lacks env), conversation history. **28% factual error rate on external knowledge.** Hallucinates fix status ("already fixed" when it wasn't). `--search` only works in interactive mode.

**Auth:** ChatGPT account auth. Only `gpt-5.4` (default) and `gpt-5.3-codex` work. `o3`/`gpt-4.1` rejected.

**Token overhead:** ~37K baseline per `codex exec` call (9 MCP servers, no disable flag). Cost-effective for substantial tasks only.

## Critical gotchas

**Turn limits (~15-20 tool calls):** Max 5 files per agent. Split larger audits. Include synthesis deadline in EVERY prompt: "After reading at most 5 files, STOP and synthesize. 70% reading, 30% writing. Partial report > no report." (6th+ recurrence, 2026-03-28). Codex doesn't see CLAUDE.md — the instruction must be in the prompt.

**Template-first anti-pattern:** Agents that create skeleton markdown first waste a write turn, then exhaust turns filling it in. Failed 3/4 sessions. Use `-o FILE` instead — captures final text message automatically.

**Memory pressure gate:** Before dispatching, count active processes (`pgrep -lf claude | wc -l`, NOT `pgrep -c` on macOS). If >= 4, reduce to sequential or audit directly.

**MCP contention:** Max 4 parallel Codex agents. Each starts 9 MCP servers. 5+ agents = 132+ simultaneous startups = system overwhelm.

**Output preservation:** Tell agents to write to `docs/audit/`, NOT `/tmp`. Immediately `git add` or `cp` after completion — sandbox cleanup can delete files. Do NOT use `--ephemeral` (deletes `-o` output).

**Verification is mandatory (Phase 3).** ~28% error rate concentrated in counts, severity, external knowledge. Code-grounded findings (file:line) are consistently reliable. See `references/verification-procedure.md` for checklist and hallucination patterns.

**S2 API outages:** Tell agents to fall back to `backend="openalex"` or exa if Semantic Scholar returns 403.

## Model selection

| Target | When | Tradeoff |
|--------|------|----------|
| `codex exec --model gpt-5.4` | Cross-referencing, counting, structured output | Free, parallel, output extraction fragile |
| Claude Code `Agent` subagents | Same + DuckDB/MCP access | Costs tokens, output inline (reliable) |
| `llmx chat --model gemini-3.1-pro-preview` | 1M context, huge file ingestion | Best for monolithic analysis |

**Use Codex for:** 5+ parallel audits, cross-file grep+read tracing, wiring/drift/completeness checks.
**Use Claude subagents for:** <3 file audits, tasks needing project-specific tooling (uv, DuckDB, MCP).

## Phase-by-phase execution

**Phase 1 -- Recon:** Read CLAUDE.md, `.claude/overviews/`, plans, `git log --oneline -30`, `docs/audit/` (skip completed). Build mental model, identify audit targets.

**Phase 2 -- Dispatch:** Craft self-contained prompts per `references/prompt-construction.md`. Execute per `references/codex-dispatch-mechanics.md`. Each prompt: "Read [files], check [properties], cross-reference [A vs B], cite file:line."

**Phase 3 -- Verify:** Every finding checked against actual code. Follow `references/verification-procedure.md`. Output: confirmed / rejected (with reason) / corrected findings.

**Phase 4 -- Plan:** Synthesize into phased execution plan per `references/plan-and-execute.md`. Fix ALL verified findings -- don't self-select "top N." Present to user; wait for approval.

**Phase 5 -- Execute:** Implement per `references/plan-and-execute.md`. Read before editing. One commit per logical change. If other agents active, commit after each fix (not batched) or use `isolation: worktree`.

## References (loaded on demand)

| File | Contents |
|------|----------|
| `references/prompt-construction.md` | Target selection categories, prompt structure, good/bad patterns |
| `references/codex-dispatch-mechanics.md` | Bash commands, flags, MCP config, `-o` caveats, fallback |
| `references/verification-procedure.md` | Verification checklist, hallucination pattern table, output format |
| `references/plan-and-execute.md` | Plan template, plan principles, execution principles, MAINTAIN.md integration |
| `references/paper-reading-dispatch.md` | DOI handling, S2 fallbacks, turn budget, GPT-5.4 strengths/weaknesses for papers |
| `references/agent-system-prompt.md` | Full system prompt for subagent dispatch |

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Commit contamination — when dispatch-research agents don't use worktree isolation, their uncommitted changes get swept into the parent session's next commit.**

---

$ARGUMENTS

<!-- knowledge-index
generated: 2026-04-08T07:17:27Z
hash: 90a4ed294c3c

cross_refs: docs/compiled/{concept-slug}.md, docs/research/*.md, research/*.md, research/adversarial-case-library.md, research/compiled/{concept-slug}.md
sources: 1
  DATA: BASE: name
table_claims: 8

end-knowledge-index -->
