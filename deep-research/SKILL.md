---
name: deep-research
description: Multi-source research with rigorous provenance tracking. Use when the user needs a literature review, evidence synthesis, deep dive, research memo, or citation-backed analysis. Find confirming/disconfirming evidence, triangulate across sources, be explicit about what's proven vs. inferred.
argument-hint: [research question or topic]
---

# Deep Research Protocol

Research with the rigor of an investigative journalist, not a search engine. Every claim needs provenance. Strong inference with explicit logical chains is fine — but say it's inference, not fact.

## Phase Structure (follow in order)

### Phase 1 — Ground Truth Audit

Before any external search, check what already exists:
- Local data, files, databases that bear on the question
- Prior reports or analysis that partially answer it
- Your own training data (labeled as such, not treated as fresh)

Output: "What I already know / have access to" inventory.
If local data contradicts a later literature finding, flag it.

### Phase 2 — Exploratory Divergence

Cast a wide net. The goal is coverage, not depth.

**Search axis requirement (mandatory):** Before searching, name ≥2 independent search axes. Different axes reach different literatures:
- **Genotype-anchored:** SNP → mechanism → intervention
- **Condition-anchored:** diagnosis → treatment evidence → candidates
- **Guideline-anchored:** clinical guidelines → standard of care
- **Mechanism-anchored:** pathway → modulators → evidence
- **Population-anchored:** "people like the user" → what worked
- **Investigation-anchored:** entity → enforcement → patterns
- **Academic-anchored:** concept → literature review → state of the art

If your axes all start from the same place, you have one axis with multiple queries, not multiple axes.

**Tool strategy (use ALL that apply):**
- **Exa:** Semantic search. Natural language phrases describing the CONCEPT, not keywords. Best for non-obvious connections and expert blog posts.
- **PubMed:** Authoritative for clinical/medical. SHORT queries (2-4 terms). Run 3-5 simple queries rather than 1 complex one.
- **Google Scholar:** Broadest coverage. Good for seminal papers and citation counts. Cross-ref with PubMed.
- **arxiv/biorxiv/medrxiv:** Preprints. Flag as [PREPRINT]. Keyword search is lossy — search by title fragments or date ranges.
- **WebFetch:** For pulling known databases (ClinVar, PharmGKB, CPIC, SEC EDGAR, etc.)
- **WebSearch:** General web for news, reports, grey literature.

**Search strategy:**
- Minimum 5 query formulations per subtopic
- Vary: semantic (Exa) vs keyword (PubMed) vs broad (Scholar)
- Read titles/abstracts from at least 20 distinct sources before forming any hypothesis
- Track which queries returned useful results and which were dead ends

Output: Raw findings list with source URLs. No synthesis yet.

### Phase 3 — Hypothesis Formation

From Phase 2 findings, form 2-3 testable hypotheses.
State each as a falsifiable claim:
- "If X is true, we should see Y in the literature."
- "If X is false, we should see Z."

### Phase 4 — Disconfirmation (mandatory)

For EACH hypothesis:
- Search specifically for contradictory evidence
- Search for: negative results, failed replications, critical reviews, methodological critiques
- Query formulations: "X does not work", "X failed", "X criticism", "X negative trial", "no association between X and Y"
- If you cannot find contradictory evidence after genuine effort, note "no contradictory evidence found" (different from "none exists")

This phase is structurally required. An output without a disconfirmation section is incomplete.

### Phase 5 — Claim-Level Verification

For every specific claim in your output:

- **Numbers:** Is this from a source, or did you generate it? If generated, label [ESTIMATED].
- **Names:** Is this author/journal/year from a source you accessed, or memory? If memory, verify or label [UNVERIFIED].
- **Existence:** Does this paper/study actually exist? If you cannot confirm, do not cite it.
- **Attribution:** Does the paper actually say what you think? Or are you interpolating?

YOU WILL FABRICATE under pressure to be precise. The pattern: real concept + invented specifics (author name, fold-change, sample size). Catch yourself. Vague truth > precise fiction.

### Phase 6 — Synthesis with Uncertainty

For each finding:
- Evidence grade (what kind of evidence supports it)
- Confidence: HIGH / MEDIUM / LOW / SPECULATIVE
- Whether confirmed, disconfirmed, or unresolved in Phase 4
- Source type: [TOOL-RETRIEVED] vs [TRAINING-DATA] vs [INFERENCE]

## Provenance Standards

Tag every claim:
- **[SOURCE: url]** — Directly sourced. Include the URL.
- **[INFERENCE]** — Logically derived from sourced facts. State the chain.
- **[UNCONFIRMED]** — Plausible but not verified. State as question or hypothesis.

Never present inference as sourced fact.

## Coverage Criteria

Adequate coverage means:
- Multiple independent research groups (not one lab)
- Positive AND negative/null results acknowledged
- Different populations / conditions considered
- Both recent (post-cutoff) and foundational (pre-cutoff) sources
- At least 3 distinct source types
- At least 2 independent search axes

If coverage is thin, say so. "I found 3 papers from one lab" is honest.

## Anti-Patterns

- **Confirmation loop:** Formed hypothesis, only searched for support
- **Authority anchoring:** Found one source and stopped
- **Precision fabrication:** Invented specific numbers under pressure to be precise
- **Author confabulation:** Remembered finding but not author, generated plausible name
- **Telephone game:** Cited primary study via review without reading the primary
- **Directionality error:** Cited real paper but inverted the sign
- **Single-axis search:** All queries from same starting point — different axes reach different literatures
- **Cruft expansion:** Added "nice to know" that buries decision-relevant claims
- **Ground truth neglect:** Went to literature without checking local data first

## Output Contract

Required sections:
1. **Decision Claims** (5-15 rows): claim, evidence type + confidence, citation ID, status tag (verified/unverified/inference/contradicted)
2. **Ground Truth** (Phase 1): What was already known
3. **Key Findings** (Phases 2-3): Each with source, evidence type, confidence, [TOOL-RETRIEVED]/[TRAINING-DATA]/[INFERENCE]
4. **Disconfirmation Results** (Phase 4): What contradictory evidence exists
5. **Verification Log** (Phase 5): Claims verified via tool, unverified from training data, caught fabricating
6. **What's Uncertain**: Unresolved questions, missing studies
7. **Search Log**: Queries run, tools used, hits/misses

## Parallel Agent Dispatch

When dispatching multiple agents:
- Split by **axis and subtopic**, not by tool
- Include ground truth context in each agent
- Always dispatch a verification agent after research agents return
- Synthesis is a separate step (agents can't see each other's output)
- 2 agents on 2 axes > 10 agents on 1 axis

## Domain-Specific Companions

- For **bio/medical** research: combine with `epistemics` skill (evidence hierarchy, anti-hallucination rules, bio failure modes)
- For **investigation/forensics**: combine with `investigate` + `competing-hypotheses` skills (uses Admiralty source grading)

## Grading Scope

This skill uses the 3-tag provenance system: `[SOURCE: url]`, `[INFERENCE]`, `[UNCONFIRMED]`.

**Precedence rule:** When `source-grading` (Admiralty `[A1]`-`[F6]`) is active — i.e., during `/investigate`, forensic, or OSINT workflows — use Admiralty grades instead of the 3-tag system. Do NOT mix both in the same output. When this skill is used standalone (literature reviews, energy research, general research memos), use the 3-tag system.

$ARGUMENTS
