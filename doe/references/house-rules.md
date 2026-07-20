# House rules this skill leans on — pointers, not copies

Per the single-invariant-definition discipline (a correctness-bearing rule gets ONE definition;
consumers load it), this file points at the canonical source for each rule rather than restating
it. If a source file moves, fix the pointer here — don't fork the content. One exception: the
heretic-before-results mechanism below is inlined directly, since its stable six-step core has no
other canonical home — see that section for the drift boundary.

## The project's own verdict grammar, if it has one (arc-agi instance: `.claude/rules/eval-conventions.md` §0)

Projects that run repeated measurement/experiment cycles often converge on a standing grading
convention — independent validity axes (e.g. sample-existence, observable-robustness, venue-power,
claim-scope-ceiling), each able to block or cap a verdict on its own. If THIS project has one,
load it BEFORE grading any result a design in this skill produces — it is the SSOT for what a
result may claim; this skill doesn't own or duplicate it. arc-agi's instance names four axes
(CELL/OBSERVABLE/VENUE/SPLIT) with a typed precedence order, not a single ordinal minimum — worth
reading as a worked example of the SHAPE such a convention can take, not as a template to copy
verbatim. **If the project has no such convention yet, that absence is itself worth naming
explicitly in the design** rather than silently assuming an equivalent exists.

## The project's own dated exhibits/phase-rule library, if it has one (arc-agi instance: `.claude/rules/eval-conventions-exhibits.md` §A-D)

Projects that accumulate measurement discipline over time often end up with a dated, enforceable
rule library organized by WHEN in a design's lifecycle each rule applies (prereg-time, run-time/
venue, verdict-time, build/dispatch-brief-time) — load it beside the verdict grammar above; it is
where the granular, incident-anchored rules live, not the top-level axes. arc-agi's instance
organizes by four phases:
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

**If the project has no such library, treat this phase breakdown (prereg / run-time / verdict /
dispatch-brief) as a starting checklist shape**, not as arc-agi-specific content — the phases
themselves are general to any repeated measurement practice.

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

## The project's own sequential-testing/stopping-rule library, if it has one (arc-agi instance: `loop/seq_stop.py`)

Projects running repeated multi-arm or sequential comparisons often build (or should build) a
tested library of stopping-rule implementations, rather than hand-deriving boundaries fresh each
time. arc-agi's instance implements: Wald SPRT boundaries (`sprt_boundaries`, `sprt_llr_binary`,
`sprt_decision`) for paired binary/sign tests; deterministic sign-test curtailment
(`sign_test_curtail`, zero-alpha, always valid — the safe default layer); O'Brien-Fleming group-
sequential boundaries (`obf_boundaries`, `obf_decision`); successive-halving rungs for multi-arm
races (`successive_halving_rungs`, `successive_halving_keep`). Use a library like this directly
for step 8's stopping-rule choice rather than hand-deriving boundaries. **If the project has no
such library, `references/classical-doe.md`'s TOST/sequential citations are the fallback
vocabulary and formal backstops — don't hand-derive boundaries from scratch either way.**

## The project's own standing-kill/decision ledger, if it has one (arc-agi instance: `.claude/rules/vetoed-decisions.md`)

Projects doing repeated experimentation often accumulate a record of previously-rejected
approaches with reopen conditions — check it before proposing or re-implementing anything it
already covers, and cite it before overturning or narrowing an existing entry. arc-agi's
convention grades each kill/cap: `KILL[measured @venue,n,reopens-if]` / `CAP[function]` /
`ARG[pending: <probe>]` — every kill or cap a design's results might feed into a standing
decision needs one of these grades, with the reopen conditions or scope stated explicitly; an
UNGRADED verdict may locate history but may not veto new work on its own. This is one worked
convention, not the only valid shape — **if the project has no such ledger, that absence is
itself worth naming**, since a design that "escapes" an undocumented prior rejection has nothing
to check itself against.

## The heretic-before-results mechanism (generic core — a project's own dispatch-protocol file, if present, wins on divergence)

Six steps, stable since first written and unchanged across this project's own churn: **(1)
discovery gate** — check whether the question is already answered before spending anything; **(2)
blind first pass** — the design's author writes their own full analysis BEFORE any external
attack call, so a later divergence is evidence, not induced agreement; **(3) a compressed packet**
(≤15KB is a reasonable default) carrying the design plus unique identifying strings (exact
numbers, coined phrasings) that make attribution checkable; **(4) ONE frontier-model call**,
backgrounded with bounded waits rather than blocking synchronously on an expensive reasoning
call; **(5) attribution by CONTENT-CORRESPONDENCE** — the response quotes the packet's own
unique strings, not merely "arrived after I sent it"; **(6) reconcile, don't adopt** — tag
integrated content by source, name every divergence explicitly, and re-derive load-bearing
arithmetic yourself before accepting it. **Excluded from this core, deliberately — these churn
and belong to the consuming project, cited not copied:** which model/vendor to call, content-type
routing between models, multi-round convergence/causal-identification requirements, wave-trigger
conditions, and dispatch-lane cost economics. **If the project has its own fuller dispatch-protocol
file, it wins on divergence** (arc-agi's instance, with these project-specific extensions:
`.claude/rules/verified-fable-dispatch.md`).
