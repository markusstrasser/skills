# Decide — artifact templates

The four durable outputs. Adapt headings to the project; keep the contract.

## 1. ADR — `docs/decisions/NNNN-<slug>.md` (the principle / why)

```markdown
# ADR NNNN — <decision in one line>

**Status:** accepted · **Date:** YYYY-MM-DD · **Session:** <id>
**Detail:** <plan path> · **Supersedes:** <prior ADRs/plans, if any>

## Decision
1. <the call, stated as a principle, not an implementation>
2. ...

## Why (grounding)
- <evidence: prior incident, data, user constraint, primary source — not "it seems better">

## Rejected — do NOT re-propose
- <alternative> → <why killed> (so the next agent doesn't re-derive it)

## Related accepted constraints
<invariants this decision must preserve>
```

## 2. Plan — `.claude/plans/<session>-<slug>.md` (the what / sequence)

```markdown
# Plan: <title> — YYYY-MM-DD
**Stance:** <breaking? compat boundary named? deepest-architecture?>  **ADR:** <link>

## Spine (dependency order — the non-negotiable core)
1. <foundational piece> ...

## Settled facts (VERIFIED — re-derive before building)
- <fact> [verified via: <the probe>]

## Work, sequenced (each phase NAMES its end-state; later phases hard-gate on earlier)
### P0 — <foundation>
<what> · **probe:** <inline grep/SQL> · **End-state:** <observable condition>
### P1 ... (gated on P0)

## Invariants
## Held AGAINST the critique (disagree-self-check log — what you rejected and why)
## First vertical slice (start here, validate before scaling)
## Probes (read-before-plan / probe-the-join — the literal commands)

## Acceptance — the `` ```verify `` gate (ENFORCED, not prose)
``verify
# stop-plan-gate.sh RUNS each non-comment line as `bash -c <line>` from the session cwd
# (30s each); ALL must exit 0 before the session can stop. This IS the plan's measurable
# exit_signal + verifier_commands — enforced, not asserted. Translate each phase's End-state
# into a runnable assertion. REAL checks only — a placeholder (`true`, a bare `echo`) defeats
# the gate and is worse than an empty block.
test -f <the artifact the plan must produce>
uv run pytest <the test that proves the behavior> -q
``
```

> The `` ```verify `` fence uses three backticks in a real plan (shown here as two to avoid
> closing this code sample). stop-plan-gate.sh is wired globally — but a plan with no verify
> block gets no enforcement, so emitting a real one is the whole point.

## 3. Deferred/open/rejected tracker — `docs/decisions/deferred-and-open.md` (living)

```markdown
# Deferred & Open Decisions — living tracker
Append + update status; mark resolved, don't delete.

**Critique audit trail:** <rounds run, what each changed, reversal count>

## Decided this session    | # | Decision | Disposition |
## Open — needs a call      | # | Question | Lean | Trigger to decide |
## Deferred — fold when X   | # | Item | Folds into | Why deferred |
## Blocked on data/external | # | Item | Unblocks when |
## Rejected — do NOT rebuild (so they're not re-proposed)
```

## 4. Vocabulary glossary (once semantics are clear — one term per concept)

A table: `| Concept | Canonical term | NOT (banned synonyms) |`. Put it in the architecture doc or a
`docs/glossary.md`. Locking one name per concept is the highest-leverage, lowest-churn naming fix —
do it instead of renaming files.

---

**Why all four:** the ADR is the *why* (survives even if the plan changes); the plan is the *what*
(executable); the tracker is the *memory* (nothing lost, nothing re-litigated); the glossary is the
*shared language* (stops drift). Skipping any one is where decisions leak back into chat-only limbo
and get re-derived three sessions later.
