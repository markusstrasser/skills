---
name: interview-prompt
disable-model-invocation: true
description: Elicit Markus's taste, beliefs, or preferences by generating high-information questions and asking only the most revealing ones. Active-learning interviewer — analyze a topic/draft/essay, brainstorm many candidate questions, sketch hypothetical answers, ask the few whose answers are most unpredictable. Use before a writing session, to seed/sharpen writing-style, to resolve a taste fork, or when "interview me about X". Routes answers into feedback memory or the writing-style corpus.
user-invocable: true
argument-hint: "[--n N] [--route feedback|writing-style|none] topic, draft path, or essay to interview about"
effort: medium
allowed-tools: [Read, Glob, Grep, Write, Edit]
---

# Interview Prompt — Active-Learning Elicitation

Front-load learning about the principal (Markus) by **asking the highest-information
questions**, instead of waiting to mine corrections reactively. Adapted from
Gwern's "interview prompt" (the GA active-learning mechanism); the theory and
scope decision live in `agent-infra/decisions/2026-06-07-guardian-angels-transfer.md`.

**Core move:** don't ask the obvious question. Generate many, predict the answers,
and ask only the ones where your prediction is uncertain or splits — those are the
datapoints that actually change the model of Markus. A question you can already
answer for him is wasted.

## When to use
- **Before a writing session** — interview Markus about the topic to surface
  angles, convictions, and phrasings he'd never have volunteered.
- **To seed or sharpen `writing-style`** — extract voice/taste rules from his
  reactions, not from guessing.
- **To resolve a taste/intent fork** — when a decision hinges on a preference
  you don't have on file (see `feedback_question_scope`: taste/intent/telos/
  risk/business-outcome are exactly the questions worth his time).
- On explicit "interview me about X" / "what should you ask me about Y".

**Not for:** implementation choices you can decide yourself, factual lookups,
or anything answerable from the corpus/memory (check first — grep memory + the
draft before asking).

## Procedure

### 1. Load context
- If the arg is a **path** (draft/essay/transcript), Read it in full.
- If a **topic**, Glob/Grep the memory dir
  (`~/.claude/projects/-Users-alien-Projects-agent-infra/memory/`) and any
  named draft for what's already known. Don't ask what's already on file.
- Note the `route` (default: infer — `writing-style` for voice/prose, `feedback`
  for working-preference, `none` to just surface answers).

### 2. Brainstorm wide (generate, don't filter)
Produce **2–3× the target N** candidate questions (default N=3, so ~6–9
candidates). Push past the first obvious ones — those are the questions every
model would ask. Aim across registers:
- **Conviction probes** — "you've implied X; where does X break for you?"
- **Forced tradeoffs** — two things he values, made to compete.
- **Counterfactuals / hypotheticals** — the curse-of-exploration killer:
  day-to-day data is predictable; hypotheticals reveal deep structure.
- **Negative space** — what he'd refuse, cut, or find embarrassing.
- **Origin** — why he believes/wants this, not just that he does.

### 3. Predict + score (the information-gain filter)
For each candidate, **silently sketch 2–3 hypothetical Markus-answers** in his
voice (use `writing-style` knowledge). Then score each question:
- **Answer variance** — do your sketched answers diverge sharply, or are they
  near-paraphrases? High divergence = you don't know = high information. (Cheap
  proxy for "verbalized-sampling" spread.)
- **Belief-update magnitude** — would a real answer add or overturn something in
  memory / writing-style? A question whose answer just confirms the file is low.
- **Reach** — does it open a vein (more follow-ups) or dead-end?

Keep the top **N** by `variance × update-magnitude`. Drop any you could confidently
answer for him — state that you dropped them and why.

### 4. Ask (only the survivors)
Ask the top N via **AskUserQuestion**, one header each, with 2–4 concrete option
hypotheses drawn from your sketched answers (he can always pick "Other"). Phrase
options as real stances, not strawmen — the point is to make disagreement easy.
Keep it to N≤3 per round; this is high-value attention, not a quiz.

### 5. Route the answers
- **`writing-style`** → propose an edit to `~/Projects/skills/writing-style/SKILL.md`
  (or its `references/`) capturing the rule his answer implies. Show the diff;
  don't auto-apply voice rules.
- **`feedback`** → write a `feedback`-type memory (Why / How-to-apply lines per
  the memory schema) and add the MEMORY.md pointer.
- **`none`** → just synthesize the answers back for the writing/decision at hand.
- Always: if an answer **contradicts** an existing memory, surface the conflict
  explicitly (append-only — mark the old one stale, don't silently overwrite).

### 6. (Optional) Follow the vein
If an answer was high-variance, one targeted follow-up is usually worth more than
a fresh question. Offer it; don't force a fixed round count.

## Quality bar
- A good session leaves a **concrete artifact** (a writing-style rule, a feedback
  memory, or sharper copy) — not just a transcript. No consumer ⇒ you asked the
  wrong questions.
- If after step 3 every candidate is low-information (you can answer them all),
  **say so and stop** — don't manufacture questions to fill N. The honest output
  is "I already have what I need on X; nothing worth your time here."

## Provenance
Mechanism: Gwern, *Guardian Angels* (gwern.net). Decision + scope:
`agent-infra/decisions/2026-06-07-guardian-angels-transfer.md`. Related:
`feedback_question_scope` (which questions are his to answer), `writing-style`
(the main consumer), `session-learning-loop-design` (the reactive counterpart —
this is the proactive front-load).
