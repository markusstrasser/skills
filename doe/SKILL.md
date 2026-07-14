---
name: doe
description: "Use when: /doe, designing a NEW experiment/probe/prereg from a hypothesis+budget — generates arms/shams/controls/bands/power/stopping-rule as a fill-in doc. Complements /eval (grades/scaffolds benchmarks) and dispatch_lint (mechanically enforces a prereg exists). NOT for grading an existing design (/eval review) or a code diff (/code-review)."
user-invocable: true
argument-hint: "[hypothesis] [budget]"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# DoE — generate an experiment design that survives its own attack

## What this is, and what it isn't

`/eval` grades and scaffolds **benchmarks** (does this instrument measure what it claims).
`dispatch_lint` **mechanically enforces** that a prereg exists before a launch is allowed to run
— refuse-to-launch, not design help. Neither one **writes the design**. `/doe` is upstream of
both: given a hypothesis and a budget, it generates the fill-in doc — arms, shams, controls,
bands, power, stopping rule — informed by a concrete, dated catalogue of how designs in THIS
project have actually failed when attacked, not a generic methodology checklist.

## Family-fit recommendation: new sibling, not an /eval extension or merge

This was an explicit open question at design time (three options considered: (a) new sibling
with a sharp boundary, (b) extend `/eval` with a DoE mode, (c) merge into one measurement skill
with modes). **Recommendation: (a), new sibling — evidenced below. Runner-up: (b), rejected on
infrastructure-coupling and content-dilution grounds, not principle.**

**Evidence — what fraction of `/eval`'s content is benchmark/judge/gold-specific vs general:**
reading `/eval/SKILL.md` in full (491 lines, 13 phase/section headers): Phase 1's design
questions are keyed on "verifier regime: deterministic ground truth or judged?", contamination
provenance tags (`authored-fresh | post-cutoff | public-lifted`), and judge-transport gotchas
(inline-not-attach payloads, judge family-neutrality, frontier judge bias rates). Phase 2 is
literally `cd ~/Projects/evals && just new-eval <slug>` — scaffolding a benchmark directory with
`PREREGISTRATION.md`, golds, and `evalcore` wiring. Phase 3 is single-gold-vs-graded-relevance on
retrieval corpora. Phase 4 is `evalcore.judge.dispatch(blind_to=...)`, panel κ, `mcnemar_exact`.
Phase 4.5 is `item_analysis.py`'s psychometric difficulty/discrimination/dispersion flags over a
scored item MATRIX. Roughly **85-90% of the skill's content and ALL of its scaffolding tooling
(`evalcore`, `just new-eval`, `DECISIONS.md`/`BENCHMARKS.md`, `item_analysis.py`) presuppose a
scored-ITEM-against-a-JUDGE-or-ORACLE measurement shape** — a benchmark, a set of golds, a panel
that scores each item. The genuinely general ~10-15% (Phase 0 dedup-before-building, "no consumer
→ don't build," "controlling A confound not THE confound," prereg-before-results, trace-reading-
before-verdict) would transfer to a live-arm comparison, but the INFRASTRUCTURE and the majority
of the specific discipline would not.

**Would tonight's four catches have been caught by `/eval`-as-is?** Checked each against `/eval`'s
own anti-pattern list: `rule-privilege-asymmetry` is a real COUSIN of `/eval`'s "judge competence
is ASYMMETRIC — validate each judge against ground truth" — but that anti-pattern is scoped to a
JUDGE MODEL's competence across benchmark items, not to whether a live ELIMINATION/SCORING RULE
itself structurally favors one experimental arm's behavior over another's; a designer applying
`/eval`'s lesson would check judge calibration, not arm-symmetric rule construction.
`scorer-mutation-suite` is a cousin of `/eval`'s "Deterministic-grader constructs (LatchBio)...
sentinel gold fields... reproduce-or-discard gold" — adjacent, but `/eval` never proposes running
adversarial gaming mutations against your own scorer before trusting it. The other 9 catalogue
entries (`negative-control-cannot-pass`, `zero-context-floor-invalidity`, `screen-entailed-floor`,
`termination-semantics-unstated`, `untransported-effect-target`, `escape-by-assertion-not-
observable`, `merge-inference-not-computed`, `reset-semantics-unspecified`, `elimination-on-
intent-not-realized-effect`) are about **live, interactive, multi-arm, multi-attempt agent
behavior measurement** (episode/state semantics, sham ladders, floor calibration across policies,
cross-venue effect transport) — a measurement shape `/eval`'s scored-item framing does not
address anywhere in its 491 lines. **Verdict: at most 2/11 catalogue entries have a plausible
cousin in `/eval`'s existing content; 9/11 are a structurally different kind of design question.**

**Why not (c), merge into one measurement skill with modes:** the real overlap (both want
prereg-before-results, both care about confound/gold validity, both want trace-reading before a
verdict) is genuine, but a merged skill either (i) internally branches on "am I grading a scored-
item benchmark or designing a live arm comparison" — moving the classification cost INSIDE one
document instead of removing it, which is not obviously cheaper than a clean file boundary, or
(ii) tries to make `evalcore`/`just new-eval`/golds/judge-panels serve BOTH shapes, which is a
genuine infrastructure misfit (there is no natural way to scaffold "3 arms of a live interactive
episode + a sham ladder + `loop/seq_stop.py` stopping rule" through a benchmark-item-and-gold
directory). `/eval`'s own doc already argues against over-embedding for exactly this reason
("bloats every context load") when explaining why it doesn't inline `evalcore`'s code — the same
argument cuts against merging a structurally different measurement shape into the same file.

**The boundary, stated precisely, for an agent choosing between them:** ask "am I scoring
INDIVIDUAL ITEMS against a gold/judge/oracle" (→ `/eval`) or "am I comparing ARMS of a live
experiment/episode and need to isolate which mechanism caused a difference" (→ `/doe`). **They
compose, not compete**, on designs that need both (tonight's `cert-distill` probe did: a
deterministic structural-diff extractor scoring generations — an `/eval`-shaped grader-validity
question — feeding a certified-vs-uncertified context ablation across live arms — a `/doe`-shaped
comparison-design question). `/doe`'s own protocol step 7 (scorer validation) explicitly hands
off to `/eval`'s grader-validity discipline rather than duplicating it — see
`references/house-rules.md`.

**The evidence base for this skill is not literature-first.** It is our own attack-caught defect
corpus (`references/failure-catalogue.md`) — every entry is a real design that looked sound at
packet stage and had a specific, load-bearing hole found by a frontier attack pass or a builder's
own re-derivation, on THIS project, dated. Classical DoE (`references/classical-doe.md`) supplies
vocabulary and formal backstops (factorial vs OFAT, blocking, randomization, TOST equivalence,
sequential boundaries) for failure classes the catalogue already names — it does not replace the
catalogue, and a design that only cites textbook DoE without checking against the catalogue is
not done.

## The protocol — fill in this template, in order

Work through these in order; each step's output feeds the next. Write the answers into a design
doc as you go — this IS the prereg, not a separate summary of it.

### 1. Construct — state precisely what mechanism is being isolated

Not "does X help" — WHICH specific causal channel does X move, and what would it look like if X
moved something else instead? (`ratchet-untransported-target`, `cert-distill-scorer-vacuity`:
both catalogue entries are exactly "the design measured a real effect, on the wrong construct.")

### 2. Arms — and the rule-privilege check

For every PAIR of arms being contrasted, ask explicitly: **are they graded under the identical
rule/instrument, or does the instrument structurally favor one arm's behavior?** A shared
grading function is not automatically a fair one — verify it is the FULL sound rule for every
arm, not tuned/scoped around the treatment arm's behavior. (`rule-privilege-asymmetry`.)

### 3. Sham ladder — isolate WHICH component, not just THAT something changed

If the treatment bundles multiple mechanisms (gating + read-back + specific content, e.g.), a
single treatment-vs-control arm cannot attribute the effect to any one of them. Build a ladder:

- **SHAM-0** (prerequisite gate, run first, cheapest): does the treatment beat the naive baseline
  AT ALL, on the SAME budget/metric? If this doesn't clear, the finer ladder is wasted spend.
- **SHAM-A / SHAM-B / SHAM-C**: each strips exactly ONE component (e.g., gate-off/schema-on,
  gate-on/read-back-off, everything-on-but-content-scrambled) — run cheapest-and-most-damning
  first (a content-scramble sham is usually the sharpest single test of "does the SPECIFIC
  content matter, or just its presence/structure"). (`sham-ladder`, `research/2026-07-14-
  composed-microloop-design.md`.)

### 4. Controls — can the negative control possibly pass?

State the grading rule, then check: under that EXACT rule, is there any way the negative control
COULD register a pass? **A control that can never pass is as broken as one that can never fail**
— both make the diagnostic vacuous. Separately: any FLOOR/ANCHOR used to size an effect must be
measured on the SAME policy/condition as the arm it anchors — a baseline borrowed from a
different regime (a different agent, a different corpus, an earlier calibration run) is not a
valid floor for THIS arm's power calculation until checked. (`negative-control-cannot-pass`,
`zero-context-floor-invalidity`.)

### 5. Screen-entailment check

If any venue/task parameter was TUNED until a baseline arm failed (a difficulty knob raised until
random play scores 0), that baseline's subsequent "failure" is not a finding — it is the
tuning criterion restated. State explicitly whether any band was calibrated by iterating against
the same data it will later be cited as evidence from. (`screen-entailed-floor`.)

### 6. Termination / transport semantics — pin them before any code

State exactly when an episode/attempt/trial ENDS and what state persists across attempts, for
EVERY arm, before writing the harness. Unstated termination semantics let different arms be
silently graded under different implicit rules — this produces headline numbers that are
individually plausible but **jointly impossible** (three claims that cannot all be true under any
single consistent rule). (`termination-semantics-unstated`.)

### 7. Scorer validation — if the verifier is a deterministic/mechanical extractor, attack it FIRST

Before trusting ANY pass/fail from a code-based (non-live-replay) verifier, run an adversarial
mutation suite: no-op, unrelated-field/random-value padding, hedged-disjunction, delete-to-
vagueness (collapse to near-empty content), evidence-copying, and one KNOWN-VALID case. The
scorer must reject the gaming mutations and accept the valid case. **If it cannot, stop — the
endpoint is invalid**, full stop, before any live query runs. Report which mutations were fixed
and which remain acknowledged, unfixed limitations — do not claim full validity you didn't
achieve. (`scorer-mutation-suite`.)

### 8. Bands and power — state the decision rule before data, size it honestly

- State SIGNAL / NULL / DEGENERATE (or equivalent) thresholds against a REAL, measured floor —
  never a borrowed or assumed one (see step 4).
- If the claim is "no effect," that needs a pre-registered **equivalence test** (TOST: both
  one-sided tests inside a stated margin), not "the difference wasn't significant" — failure to
  reject a null is not evidence of equivalence. (`classical-doe.md` §TOST.)
- Compute actual power/CI arithmetic for the stated n — don't eyeball a threshold. `loop/
  seq_stop.py` has ready SPRT (Wald boundaries) / O'Brien-Fleming / successive-halving
  implementations if a sequential design is the right shape; state explicitly whether you're
  using fixed-n or sequential stopping and why.

### 9. Effect-target transport — never assume Δ_here = Δ_there without justifying it

If the target effect size for a power calculation is measured in a DIFFERENT venue/instrument's
units (a real-world board score, a different corpus, a historical policy), state explicitly why
that number transfers to THIS venue's units — or treat the transform itself as unknown and report
the result as scoped to THIS venue only. (`untransported-effect-target` — this is the single
most consequential catalogue entry: an entire "powered null" headline inverted once this was
checked.)

### 10. Escape-a-kill check

If this design's premise is "this mechanism escapes a previously-killed approach because it's
structurally different," that escape must be demonstrated by the design's OBSERVABLES — not
merely argued in the packet's prose. Name the specific observable that would fire if the escape
were illusory (the killed mechanism reappearing under a different name), and check for it.
(`escape-by-assertion-not-observable`.)

### 11. Heretic-before-results

Once the design clears 1-10, get it attacked BEFORE any results land (`.claude/rules/verified-
fable-dispatch.md` for the two-stage frontier-attack protocol in this repo; `eval-conventions-
exhibits.md` §C "Heretic-before-results"). A design this skill produces is a draft until it has
survived one adversarial pass — the catalogue exists because that pass reliably finds real holes,
including in designs written with this exact checklist in hand (see the worked example).

## Where the depth lives

- **`references/failure-catalogue.md`** — the full, dated, quoted catalogue every numbered step
  above cites by tag. Read the entries, not just the tag names — the exact quoted language is
  what makes each one checkable against a new design.
- **`references/house-rules.md`** — pointers (not copies, per the single-invariant-definition
  discipline) into `eval-conventions.md` §0 four-axis grammar, the exhibits §A-D tables,
  `loop/seq_stop.py`, and `vetoed-decisions.md`'s verdict grammar (KILL[measured]/CAP/ARG).
- **`references/classical-doe.md`** — the short canon pass (Fisher, TOST, sequential/optimal
  design) with each citation mapped to the catalogue failure class it formally backs.
- **`examples/worked-constructed-h.md`** — the protocol applied end-to-end to a real, live
  in-repo design (`active-goalid` rung 4, "constructed-H"), diffed against the actual packet that
  was independently written for it — shows where the template would have caught the same holes
  the real attack found, and where it wouldn't have.

## What this skill does NOT do

It does not run experiments, dispatch frontier attacks, or grade results — it produces the design
doc a human or agent then executes (possibly via `/eval`'s Phase 2-5 machinery once the design
exists) and gets attacked (via the verified-fable-dispatch protocol). It is not a replacement for
`dispatch_lint`'s mechanical refuse-to-launch gate — a design produced here should still pass
that gate before spending.

---
**Hit a defect or friction in THIS skill during a design arc?** Log it so the next run inherits
the fix — append a dated entry to `references/failure-catalogue.md` with the same quote-and-tag
discipline as the existing entries, not a new file.
