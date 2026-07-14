# House rules this skill leans on — pointers, not copies

Per the single-invariant-definition discipline (a correctness-bearing rule gets ONE definition;
consumers load it), this file points at the canonical source for each rule rather than restating
it. If a source file moves, fix the pointer here — don't fork the content.

## `.claude/rules/eval-conventions.md` §0 — the four-axis verdict grammar

Every measurement result is graded on four independent axes (CELL validity, OBSERVABLE
throughput-sensitivity, VENUE power, SPLIT claim-ceiling); a claim is capped by its weakest axis.
Load this BEFORE grading any result a design in this skill produces — it is the SSOT for what a
result is even allowed to claim. Precedence rules (a dead cell beats a good-looking number; a
floored positive control voids a comparison rather than booking a negative; split caps
everything) are stated there, not restated here.

## `.claude/rules/eval-conventions-exhibits.md` §A-D

Dated, enforceable rules organized by phase:
- **§A Prereg-time** — floor-anchored bars (never a round number), pooled rule-bearing mass,
  target-power screens, venue power flags, formal-anchors citations, **heretic-before-results**
  (a $0 cross-model attack AFTER bands freeze but BEFORE results land — this is the mechanism
  `/doe`'s protocol step 11 invokes), oracle-before-build ordering, build-readiness ≠ data-
  availability, pre-spend intervention sweeps.
- **§B Run-time/venue** — transport preflight before any multi-arm spend, venue comparability
  under contention, information-ordered schedules, watcher arm-time pairs (synthetic positive +
  current-log zero-match before trusting a monitor).
- **§C Verdict-time** — the four budget confounds (frontier-starvation/thinking-burn/wall-
  binding/plumbing-death), content probes before blaming a resource layer, plumbing-wall root-
  cause discipline, PROVISIONAL-before-heretic tagging, real-model-response controls before any
  paid deploy, the "instrument's own gates first" rule (verify a stated calibration gate actually
  ran before trusting a graded result).
- **§D Build/dispatch briefs** — Wall→Scholar+Library+Registry, negative controls in every
  dispatched instrument brief, builder-flags-amend-prereg.

## `~/Projects/skills/eval/SKILL.md` — the scorer/grader/gold validity discipline

`/doe`'s protocol step 7 (scorer validation) hands off to `/eval` rather than duplicating it: if
the verifier in play is a scored-item-against-a-gold/judge instrument (not a live multi-arm
behavioral comparison), `/eval`'s Phase 1 verifier-regime questions, Phase 4.5's
`item_analysis.py` (INSPECT-GOLD/CEILING/FLOOR/TOP-DISPERSION flags), and its "Deterministic-
grader constructs (LatchBio)" anti-pattern are the canonical source — read them there. `/doe`'s
own `scorer-mutation-suite` catalogue entry is an ADDITIONAL, sharper check for a narrower class
`/eval` doesn't cover: adversarially validating a deterministic structural extractor / self-
issued-certificate scorer (not a benchmark gold) with explicit gaming mutations before trusting
it inside a live-arm comparison. See `SKILL.md`'s "Family-fit recommendation" section for the
full boundary evidence and why this is a hand-off, not a duplication.

## `loop/seq_stop.py`

Pure, tested implementations of: Wald SPRT boundaries (`sprt_boundaries`, `sprt_llr_binary`,
`sprt_decision`) for paired binary/sign tests; deterministic sign-test curtailment
(`sign_test_curtail`, zero-alpha, always valid — the safe default layer); O'Brien-Fleming group-
sequential boundaries (`obf_boundaries`, `obf_decision`); successive-halving rungs for multi-arm
races (`successive_halving_rungs`, `successive_halving_keep`). Use these directly for step 8's
stopping-rule choice rather than hand-deriving boundaries — they're selftested against known
reference values.

## `.claude/rules/vetoed-decisions.md` — the verdict grammar

`KILL[measured @venue,n,reopens-if]` / `CAP[function]` / `ARG[pending: <probe>]` — every kill or
cap a design's results might feed into a standing decision needs one of these grades, with the
reopen conditions or scope stated explicitly. An UNGRADED verdict may locate history but may not
veto new work on its own. A design produced by this skill that proposes overturning or narrowing
an existing entry should cite the entry's exact grade and address its stated reopen conditions,
not just its headline.

## `.claude/rules/verified-fable-dispatch.md` — the two-stage frontier-attack protocol

The mechanism behind protocol step 11 (heretic-before-results): discovery gate → blind design
pass BEFORE any external call → ≤15KB adversarial packet → ONE frontier call (backgrounded,
synchronous bounded waits) → attribution by content-correspondence → reconciliation with named
divergences. Every catalogue entry in `failure-catalogue.md` was caught by exactly this
mechanism, or by a builder re-deriving the same class of check unprompted after having been
caught by it once already (`termination-semantics-unstated`'s fix, applied proactively one rung
later).
