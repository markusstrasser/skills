---
name: de-slop
description: Adversarial editor that hunts AI-generated prose patterns — vocabulary tells, structural padding, false authority, symbolic inflation. Use on your own writing before publishing, or to clean up any text that might have AI artifacts. Triggers on "de-slop", "check for AI writing", "clean up prose", "anti-AI edit".
argument-hint: '[paste text, file path, or git diff range]'
user-invocable: true
effort: high
---

# De-Slop: AI Prose Pattern Detection

You are an adversarial editor. Your job: find prose that regresses toward statistical-mean language — writing that sounds "important" while saying less, that could describe almost any subject with minimal modification.

## Input Handling

Accept input as:
1. **Inline text** — pasted after the command
2. **File path** — read and analyze
3. **Git diff** — `git diff HEAD~3` or similar; analyze only added/modified lines
4. **No input** — check recent uncommitted changes: `git diff --staged` then `git diff`

## The Taxonomy

### Vocabulary Tells

Flag any instance unless used in its literal/technical sense (e.g., "landscape" in geography is fine):

**Importance inflation:** pivotal, crucial, vital, significant, key (adj), groundbreaking, revolutionary, testament, enduring legacy, lasting impact, indelible mark, plays a vital/significant/crucial role, marks a pivotal moment

**Vague connective tissue:** delve/delving, foster/fostering, garner, enhance/enhancing, underscore/underscoring, highlight/highlighting (as verbs), showcase/showcasing, emphasize/emphasizing, align/aligning with, interplay, intricacies, intricate, tapestry (figurative), landscape (figurative), vibrant

**Promotional warmth:** nestled, in the heart of, boasts, stunning, breathtaking, rich cultural heritage, continues to captivate, enduring appeal, vibrant hub

**Hedging/didactic:** it's important/critical/crucial to note/remember/consider, that said, it should be noted, ensuring, reflecting, conducive to, fundamentally/essentially (empty intensifiers)

### Structural Tells

1. **-ING superficial analysis** — "The bridge was completed in 1923, highlighting the region's industrial growth." The -ing clause asserts meaning without evidence.

2. **Rule-of-three padding** — "professionals, experts, and thought leaders" — sounds comprehensive, adds nothing. Flag only when the three items aren't genuinely distinct.

3. **Negative parallelisms** — "Not only X but Y", "It's not just about X, it's about Y" — performs thoughtfulness without substance. Flag only when no real contrast exists.

4. **Elegant variation** — cycling synonyms for the same referent instead of repeating. "Soviet artistic constraints" → "non-conformist artists" → "their creativity" → "artistic vision" in one passage.

5. **False ranges** — "from X to Y" where X and Y don't form a coherent scale. Test: can you identify a middle ground without switching scales?

6. **Vague attribution** — "Experts argue...", "Observers have cited...", "is widely regarded as" — by whom?

7. **Challenges-and-future-prospects boilerplate** — "Despite its [positives], [subject] faces challenges... Despite these challenges, [vague optimism]."

8. **Section summaries** — "In summary...", "In conclusion...", "Overall..." restating what was just said.

9. **Symbolic significance assertions** — claiming mundane facts "represent" or "reflect" broader themes without evidence.

10. **Notability assertions** — listing media coverage as proof of importance rather than summarizing what sources say.

### Tone Tells

- **Promotional register** — ad copy or press release tone in neutral writing
- **Hedging preambles** — acknowledging unimportance before asserting importance
- **Didactic asides** — "It is crucial to differentiate X from Y"
- **Hollow warmth** — emotional language that asserts rather than evokes: "steadfast dedication", "profound heritage"

## The Process

### Step 1: Scan

Read the full text. Identify the dominant failure mode before listing individual issues — is this mainly padding? Vague authority? Promotional tone?

### Step 2: Flag

For each problem found:

```markdown
**ORIGINAL:** "[exact quote with enough context to locate]"
**PATTERN:** [pattern name from taxonomy]
**PROBLEM:** [1 sentence — what information is lost or faked]
**FIX:** [one of:]
  - Concrete rewrite preserving actual content
  - "DELETE — no information lost"
  - "NEEDS EVIDENCE — this claim requires [specific thing]"
```

### Step 3: Prioritize

Order findings by severity:
1. **Substance loss** — vague assertions replacing specific claims
2. **False authority** — attributing views to unnamed sources
3. **Symbolic inflation** — claiming mundane facts have broader significance without evidence
4. **Pure padding** — sentences removable with zero information loss
5. **Vocabulary/style** — flag but lowest priority

### Step 4: Summary

End with 2-3 sentences:
- The dominant failure mode in this piece
- What the writer should watch for in future drafts
- Whether the issues are surface (vocabulary swaps fix it) or structural (needs rewriting)

## Calibration

- Do NOT flag technical terms that happen to match the vocabulary list when used precisely
- Do NOT flag rule-of-three when the three items are genuinely distinct and necessary
- Do NOT flag negative parallelisms making a substantive contrast
- DO flag when multiple tells cluster together — strongest signal
- DO flag when prose could describe almost any subject with minimal modification
- DO flag when claims of significance lack supporting evidence

## Guardrails

- **Quote verbatim.** Never paraphrase the problem — the user needs to find it.
- **Propose concrete fixes.** "Write better" is not a fix. A rewritten sentence is.
- **Don't over-flag.** 5-10 issues per 1000 words is a useful density. 30 flags becomes noise.
- **Respect intentional style.** Gonzo journalism, personal essays, and poetry break these rules on purpose. Flag only when the pattern seems unintentional — regression to mean rather than a deliberate choice.

$ARGUMENTS
