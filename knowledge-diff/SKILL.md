---
name: knowledge-diff
description: Extract only novel information from text — what's NOT in your training data. Use when reading articles, papers, transcripts, or notes and wanting the delta. Triggers on "what's new here", "knowledge diff", "what don't you know".
argument-hint: '[paste text, or provide file path / URL]'
user-invocable: true
effort: low
---

# Knowledge Diff

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
- **2024–cutoff:** Partially in training. Medium reliability. Flag with `[UNCERTAIN — may be in training]` when unsure.
- **Post-cutoff:** Genuinely novel. High delta density expected. Most valuable use case.
- **Private/unpublished content:** Always novel regardless of date. Highest reliability.

**The fundamental honesty problem:** You cannot reliably introspect on your own knowledge boundaries (SimpleQA: ~72% accuracy across frontier models — 28% of "confident" factual answers are wrong). This skill works best when the content is *obviously* outside your training (post-cutoff, private, niche domain). For borderline cases, state uncertainty rather than guessing.

**Optional verification:** If `verify_claim` is available, spot-check 2-3 extracted "novel" claims. If Exa/Brave finds them in multiple pre-cutoff sources, they're probably not novel — you just failed to recall them. Reclassify as `[IN TRAINING — failed to recall]`.

## The Process

### Step 1: Read and Internalize

Read the full text. Note the publication date if available — this calibrates your confidence in the self-test.

### Step 2: Self-Test

For each candidate statement, apply this filter:

> "Could I produce this claim as an answer to a direct question, WITHOUT having seen this text, purely from pre-training?"

- **Yes → exclude.** This is already in your weights.
- **Uncertain → include with caveat.** Tag `[UNCERTAIN]` — may be in training but you can't confirm.
- **No → include.** This is the delta.

Edge cases:
- **Known concept, novel application:** Include. "Transformers can do X" might be novel even if you know transformers.
- **Known fact, novel framing:** Include only if the framing itself is the insight. Not: "DNA is a double helix" reworded. Yes: a genuinely different causal model of a known phenomenon.
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

- **No summarizing.** This is not a summary. A summary captures the text's main points. A diff captures only what's NEW relative to your knowledge. A well-known topic might produce zero diff from a 5000-word article.
- **No hedging inflation.** Don't include things "just in case" you might not know them. If you're >90% confident you'd produce it from training, exclude it. But DO include with `[UNCERTAIN]` when genuinely unsure — false negatives (missing real delta) are worse than false positives.
- **No editorial commentary.** Don't evaluate whether the novel claims are correct — just extract them. The user decides what to do with the delta.
- **Preserve the author's precision.** If the source says "37.2%", don't round to "about 37%". The specificity IS the delta.
- **State the date.** Always note the source's publication date (if known) and your training cutoff in the output header. This lets the user calibrate how much to trust the diff.

$ARGUMENTS
