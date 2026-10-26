---
name: doe
description: "Use when: /doe, designing a NEW experiment/probe/prereg from a hypothesis+budget — generates arms/shams/controls/bands/power/stopping-rule as a fill-in doc. Complements /eval (grades/scaffolds benchmarks) and dispatch_lint (mechanically enforces a prereg exists). NOT for grading an existing design (/eval review) or a code diff (/diff-review)."
user-invocable: true
argument-hint: "[hypothesis] [budget]"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# DoE — generate an experiment design that survives its own attack

Given a hypothesis and a budget, write the fill-in design doc (arms, shams, controls, bands, power, stopping rule), checked against `references/failure-catalogue.md`: this project's own dated, attack-caught design defects. `/eval` grades and scaffolds benchmarks; `dispatch_lint` refuses launches without a prereg; neither writes the design.

**Boundary:** scoring INDIVIDUAL ITEMS against a gold/judge/oracle → `/eval`. Comparing ARMS of a live experiment/episode to isolate which mechanism caused a difference → `/doe`. They compose: step 7 hands grader validity to `/eval`'s discipline. Why this is a sibling skill rather than an `/eval` mode: `references/family-fit.md`.

The catalogue is the evidence base. Classical DoE (`references/classical-doe.md`) supplies vocabulary and formal backstops; a design that cites textbook DoE without checking the catalogue is not done.

**Full wording, evidence and incident detail for every step below: `references/protocol-full.md`.** Read a step's full text there when the step fires on your design and the one-liner leaves the check ambiguous. Read the catalogue entries behind the tags, not just the tag names: their quoted language makes each check applicable.

## The protocol — fill in this template, in order

Write the answers into the design doc as you go; this IS the prereg, not a summary of it.

### 1. Construct
Name WHICH causal channel X moves, and what the result would look like if X moved something else. (`ratchet-untransported-target`, `cert-distill-scorer-vacuity`.)

### 2. Arms — rule-privilege check
For every contrasted PAIR of arms: are they graded under the identical, FULL sound rule, or does the instrument structurally favor one arm's behavior? A shared function is not automatically fair. (`rule-privilege-asymmetry`.)

### 3. Sham ladder
- Bundled treatment → one treatment-vs-control arm cannot attribute the effect; build a ladder.
- **SHAM-0** first (cheapest): does treatment beat the naive baseline at all, same budget/metric? If not, stop.
- **SHAM-A/B/C**: each strips exactly ONE component; run cheapest-and-most-damning first (content-scramble usually sharpest). (`sham-integrity`.)
- **Treatment information budget**: for any arm that compresses/summarizes context, compute per-unit tokens (total ÷ units) and name the primitives the observable needs; if they cannot fit, the arm is STARVED and the design measures compression loss. (`treatment-starvation`.)

### 4. Controls
- Under the EXACT grading rule, can the negative control possibly pass? A control that can never pass is as broken as one that can never fail. (`negative-control-cannot-pass`.)
- Any floor/anchor sizing an effect must be measured on the SAME policy/condition as the arm it anchors; a borrowed baseline is invalid until checked. (`zero-context-floor-invalidity`.)

### 4a. Dependency-claim verification
- Every "already exists / already provides / X carries Y / converter closes items N-M" sentence is a CODE FACT: verify it AT the cited artifact before it justifies a formula, checklist item or ratification.
- Verify the ENUMERATION of legal values, not just a field's presence.
- Re-run the check at LAUNCH for any dependency that did not exist at design time. (`dependency-claim-unverified`, `prose-asserts-a-code-fact`.)
- Name the verification mode per claim: **grep** (static existence/enumeration), **derivation** (structural/math relation: compare actual definitions), **runtime assert with declared fallback** (resource from a stochastic process). A claim naming no mode is unverified.

### 4b. Eligibility-provenance and witness-pair tables (both mandatory)
- **Eligibility-provenance**, one row per measured quantity: what decides inclusion in its scored/denominator set; is that fixed independent of arm behavior? If not, argue treatment-independence or flag it INADMISSIBLE as a primary observable on that stratum.
- **Witness-pair**, one row per gate/bound/threshold/falsifier: one concrete reachable PASS input and one FAIL input.
- "N/A — no gates / no arm-dependent quantities" is a legal row, not an exemption. Run the project's refuse-to-launch gate (arc-agi: `just dispatch-lint`) before spend.

### 5. Screen-entailment
If a venue/task parameter was tuned until a baseline failed, that failure is the tuning criterion restated. State whether any band was calibrated on the data it will be cited from. (`screen-entailed-floor`.)

### 6. Termination / transport semantics — before any code
- For EVERY arm, state when an episode/attempt/trial ENDS and what persists across attempts; unstated semantics yield jointly impossible headline numbers. (`termination-semantics-unstated`.)
- Cross-harness/cross-system comparisons: pin each arm's transport provenance (client, system prompt, session persistence) from the reference run's own config/run.json, not assumption.

### 7. Scorer validation — attack a mechanical verifier FIRST
- Before trusting a code-based verifier, run the mutation suite: no-op, unrelated-field/random padding, hedged disjunction, delete-to-vagueness, evidence-copying, **polarity/negation flip**, plus one KNOWN-VALID case.
- Tier every mutation: **MUST-REJECT** (no-op, delete-to-vagueness, anything that structurally voids the instrument; one acceptance stops the design before any live query) vs **NAMED-RESIDUAL** (caps the role).
- An instrument with accepted residuals is never a reward-signal input (screen/instrumentation/triage only), and its headline reports "N residuals accepted, capped at [role]"; a bare "X/X passed" hiding a residual is a defect.
- A LABELING instrument (output feeds a persistent dataset label) also owes a hand-graded calibration sample before the dataset ships and a DIFFERING-INPUT positive control. (`scorer-mutation-suite`, `polarity-blind-labeling-instrument`.)
- Grader-validity method beyond this: `/eval` (see `references/house-rules.md`).

### 7a. Objective dry-run
- A reward/score composed from branches/factors (ternary, gated `+1/0/−λ`, any `∀`/`∃` over a set): hand-build (i) a genuine full-process win, (ii) a silent/degenerate win, (iii) an empty/no-op trajectory; evaluate the ACTUAL formula with the ACTUAL shipped computers; require (i) > (ii) ≥ (iii).
- If any quantified-over input is not yet working code, the dry-run is not dischargeable: paper re-check may proceed, but no checklist may call the formula "closed" or "reward-safe".
- Extend the dry-run to every summary statistic and encoding at its actual operating point (e.g. MAD collapses to 0 when >50% of mass is modal; sentinel values can collide with legitimate domain values).

### 8. Bands and power
- SIGNAL / NULL / DEGENERATE thresholds against a REAL measured floor (step 4).
- "No effect" needs a pre-registered equivalence test (TOST), not a non-significant difference. (`classical-doe.md` §TOST.)
- Compute power/CI for the stated n; state fixed-n vs sequential and why (`loop/seq_stop.py`: SPRT, O'Brien-Fleming, successive halving).
- **Agent-run arms**: size n from measured run-to-run spread, piloted where the arms actually score (spread peaks near half of attainable score).
- Loop-policy arms (fork, restart, tree search, long session) need equal-compute controls: one long run AND the same budget as independent best-of-N runs.
- Best-of-N/fork arms select winners by the deployment rule (validation score or the agent's own pick), never the hidden test.
- Claims about an *idea* need ≥2 fresh-session implementations per idea arm.

### 8a. Runtime semantics
- Paid APIs/GPUs: freeze a hard external spend circuit breaker. Local `$0` work: derive the wall from `calibration × workload ratio × safety factor` (or a startup throughput probe) and use a progress-aware stall watchdog, not a round number.
- A watchdog kill is runtime invalidity, never capability zero; resume from the last immutable checkpoint, never silently shrink the budget.
- If fixed wall is part of the construct, label it a treatment variable and match it across arms; otherwise keep it out of capability bands. (`fixed-wall-as-cost-ceiling`.)

### 9. Effect-target transport
If the target effect size comes from a different venue/instrument, justify why it transfers to THIS venue's units, or treat the transform as unknown and scope the result to this venue. (`untransported-effect-target`, the most consequential entry.)

### 10. Escape-a-kill
- If the premise is "escapes a previously killed approach", name the observable that would fire if the escape were illusory, and check it. (`escape-by-assertion-not-observable`.)
- After drafting any MUST-NOT/exclusion principle, re-apply it mechanically to every other mechanism in the same packet, your preferred one included.

### 11. Heretic-before-results
- After 1-10, get the design attacked BEFORE results: the project's dispatch-protocol file if it has one (arc-agi: `.claude/rules/verified-fable-dispatch.md`), else the six-step mechanism in `references/house-rules.md`; grade findings with the project's verdict grammar (arc-agi: `eval-conventions-exhibits.md` §C). The design is a draft until it survives one adversarial pass.
- Decision tables freeze as EXECUTABLE CODE: one module with an exhaustive property test over its enumerable state space, prose stamped "documentation — module wins on divergence", module sha pinned in the launch descriptor. Default for every prereg with a decision table.
- Probe tier (n=1/cell, $0): budget ~2 dual-lane attack rounds and accept residual risk carried by the executable tests; reserve convergence-to-clean cycles for decision-gating or spend-bearing designs.

## Scope the protocol to the spend

Full weight at $18+ component designs (every step fired). At $0 screening probes and reused-instrument calibrations:
- Steps 2 and 5 → one-line confirmation when there is no paired-arm contest or tuned venue.
- Steps 3 and 6 → N/A for single-instrument calibration (no episode boundary, no bundled treatment).
- Step 8 → one hand-graded sample with a Wilson CI; full TOST/`seq_stop.py` is for $50+ decisions.
- Steps 9 and 10 → usually N/A, UNLESS the probe sits next to a standing KILL: then step 10 is the most important step (state how the probe's object differs, name the observable that would show it becoming the killed thing).
- Step 11 → a cheap-lane sanity pass when grading against frozen hand-graded bands.

Steps 1, 4/4a and 7/7a are load-bearing at EVERY tier: never skip them.

## Where the depth lives

- `references/failure-catalogue.md` — read when a step cites a tag: the full dated, quoted entries.
- `references/protocol-full.md` — read when a step fires and its one-liner is ambiguous: full step wording, evidence, worked incidents, tier-scoping rationale.
- `references/house-rules.md` — read at steps 7 and 11 and when citing a verdict: pointers into the project's verdict grammar, exhibits, `loop/seq_stop.py`, kill ledger, plus the project-agnostic six-step heretic mechanism.
- `references/classical-doe.md` — read when you need formal backing (factorial vs OFAT, blocking, TOST, sequential/optimal design) mapped to catalogue classes.
- `examples/worked-constructed-h.md` — read before your first design in a session: the protocol applied end-to-end and diffed against a real attacked packet.
- `references/family-fit.md` — why `/doe` is a sibling of `/eval`, not a mode.

## What this skill does NOT do

It does not run experiments, dispatch attacks or grade results; it produces the design doc someone executes (possibly via `/eval` Phases 2-5) and gets attacked. It does not replace `dispatch_lint`: the design must still pass that gate before spend.

---
**Hit a defect or friction in THIS skill during a design arc?** Log it so the next run inherits
the fix — append a dated entry to `references/failure-catalogue.md` with the same quote-and-tag
discipline as the existing entries, not a new file.
