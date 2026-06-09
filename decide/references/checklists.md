# Decide — the two non-optional checklists

These run on every decision, including `--quick`. They are the anti-sycophancy and anti-drop core.

## Disagree-self-check (Phase 4, after every critique round)

For EACH finding from a reviewer (model or subagent), before folding or rejecting:

```
DISAGREE SELF-CHECK:
  finding: <one sentence>
  my prior position: <one sentence>
  is the claim verified in code? yes/no — <the grep/SQL that confirms or refutes it>
  new evidence beyond "the reviewer said so"? yes/no — <the specific fact>
  cross-model agreement? yes/no
  action: FOLD / HOLD / PARTIAL
  if HOLD: what context did I have that the reviewer lacked? <one sentence>
  if FOLD: name the new fact that drives it (NOT "said with conviction")
```

Rules:
- **Verify before fold.** Model line-numbers and symbol names lie; the critique verifier inflates
  "hallucinated." Rank by convergence + code-verification, NEVER the confidence field.
- **A flip needs a new fact.** "The model was confident" / "it sounds right" is not a fact. Sycophantic
  flips dressed as reasoning updates are the exact failure this catches (FM7).
- **HOLD is a valid, common answer.** Reviewers have less project context than you. Record what you held
  against and why — that log is part of the artifact.
- **Reversal vs detail.** Did the finding overturn the *spine* (a reversal) or specify a *HOW* one level
  down (detail)? Track the count of genuine reversals — that, not the finding count, is the quality signal.

## Completeness-and-capture check (Phase 5, before declaring the decision closed)

Do NOT assert completeness — mechanically verify it:

```
COMPLETENESS CHECK:
  [ ] List every substantive thread/decision/option raised this session (scroll back; don't trust memory).
  [ ] For each: is it in a DURABLE, COMMITTED doc (ADR / plan / tracker / glossary)? Name the file.
  [ ] git status — are the artifacts actually committed, or untracked/uncommitted? (orphan risk)
  [ ] Were any options generated then dropped without a disposition? Triage them: decided/deferred/rejected.
  [ ] Does every rejected item carry a reason (so it's not re-proposed)?
  [ ] Does the plan name a first vertical slice + per-phase end-states?
```

Failure signatures this catches (all seen in real sessions):
- Research/brainstorm memos written by subagents but left **untracked** (lost on a clean).
- Brainstorm directions ranked but the **lower-ranked ones never triaged** (orphaned in a memo).
- A decision discussed in chat but never written to an ADR (lives only in the transcript → lost at compaction).

If anything fails, fix it before declaring done. The deliverable is the committed artifact set, not the synthesis.
