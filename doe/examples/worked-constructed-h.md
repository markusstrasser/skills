# Worked example — applying the /doe protocol to `active-goalid` constructed-H (rung 4)

Source design: `research/external/2026-07-14-active-goalid-constructedh-packet.md` — a real,
live, in-repo design (not a toy). This rung follows THREE prior attacked rounds in the same
lineage (`active-goalid-objective-life`, `-reachability-venue`, `-game-tier`, all closed), so its
author was writing with the earlier rounds' lessons already in hand — a fair test of whether
this skill's protocol catches anything a genuinely attack-hardened designer already missed, or
whether it only restates what good practice already produces.

## Walking the 11 steps against the packet

**1. Construct** — packet states the deliverable precisely: "the constructed-vs-planted gap...
IS the deliverable — the first measured number in this whole research line for 'how much does
discovering H, not just resolving it, cost.'" **✓ Satisfied**, stated as clearly as the protocol
asks.

**2. Rule-privilege check** — the packet is explicit that planner-over-constructed-H and
planner-over-planted-H share "the SAME planner." **Gap the protocol surfaces that the packet's
own open questions don't name:** the packet's success shape excludes COVERAGE MISSES from the
identification-rate denominator for the constructed-H arm ("a coverage MISS... is excluded from
the identification-rate denominator for that venue"). But planted-H has coverage=100% by
construction (the true index is always in the declared set) — the exclusion rule can NEVER fire
for the ceiling arm, only for the constructed arm. The two arms' identification-rate denominators
are therefore structurally asymmetric: the ceiling arm's rate is computed over ALL its trials,
the treatment arm's rate is computed over a SELF-SELECTED (coverage-passing) subset of its
trials. This doesn't necessarily invalidate the design (coverage is reported separately, per the
packet's own text), but the GAP measurement (constructed vs. planted rate) needs to state whether
it's comparing "identification rate given coverage" (fair) or accidentally comparing rates over
different-sized denominators (not fair) — worth a one-line clarification the packet doesn't have.

**3. Sham ladder** — the generator-vacuity control (a degenerate `CONTACT[exit]`/always-True
proposal, checked for 0% coverage/0% identification) is exactly a SHAM-0-shaped prerequisite
gate, and the packet explicitly treats it as one ("this control runs and is graded BEFORE the
real generator's headline number is reported as meaningful"). **Gap the protocol surfaces:** no
SHAM-A/B/C-style isolation of WHICH component of the real constructor (sweep-based exploration
vs. the RECOLOR-specific segmentation-diff filter vs. the extensional-equivalence check) is doing
the work if the real generator succeeds. The packet's own open question #2 gestures at a
"subtler degenerate generator" concern but stops short of proposing the isolating arm: a
generator that proposes EVERY touched object as a candidate (no recolor filter) would test
whether the RECOLOR signal specifically matters, or whether "touched at all" is doing equivalent
work — a cheap, concrete SHAM-A the packet doesn't include.

**4. Controls** — the negative control is checked for whether it CAN register a non-zero pass
("If the degenerate generator's bands come out non-zero on any venue, the bands themselves are
unfailable and must be redesigned") — correctly avoids the `negative-control-cannot-pass` trap.
The floor/anchor question: `gt02`/`gt03` are explicitly excluded from graded bands as
dev-burned, with fresh venues supplying the actual numbers — correctly avoids
`zero-context-floor-invalidity`. **✓ Both sub-checks satisfied, and satisfied BY NAME** (the
packet uses "dev-burned," "in-sample sanity," almost the exact vocabulary this skill's catalogue
uses — direct evidence the lesson transferred forward within the lineage).

**5. Screen-entailment** — fresh venues reuse `build_gt03.py`'s validated topology via a single
pinned-seed generation pass, explicitly contrasted with the earlier rounds' "multiple
discard-and-retry rounds" — correctly avoids tuning-until-it-works. **✓ Satisfied, explicitly
reasoned** (the packet states WHY this avoids the earlier trap, not just that it does).

**6. Termination/transport semantics** — stated in the packet's SECOND section, before any
generator/venue content, explicitly citing this as "the fix that a fable attack had to force me
to make explicit last time; doing it before any code is written this time." **✓ Satisfied,
exemplary** — this is the catalogue's `termination-semantics-unstated` lesson, visibly learned
and applied proactively one rung later.

**7. Scorer validation** — the extensional-equivalence checker (`gate_open = h_true in touched`,
via a position-lookup mapping a recoloring object to a formal switch index) is a deterministic
verifier used to certify "coverage." **Gap the protocol surfaces:** no adversarial mutation test
of the position-lookup itself — e.g., a deliberately near-miss object (spatially adjacent to the
true switch, or sharing a bounding box after segmentation noise) that SHOULD be rejected by the
mapper but might not be. The packet's open question #1 raises a related but different concern
("does this smuggle experimenter knowledge") — a validity worry about the CONCEPT, not a
concrete adversarial TEST of the implementation the way `scorer-mutation-suite` demands. This is
a cheap, addable check: construct 2-3 synthetic near-miss objects and confirm the mapper
correctly returns "no match," before trusting any real coverage number.

**8. Bands/power** — the success shape (coverage AND identification, kept separate) is defined
per-cell; the packet excerpt reviewed here does not show an explicit power/n statement (a
"Bands" section is referenced but not captured in this worked example's source excerpt) — **not
assessed**, flagged rather than assumed either way.

**9. Effect-target transport** — not applicable to this rung (a local coverage/identification
measurement, no cross-venue effect size being sized) — the protocol step correctly returns N/A
rather than manufacturing a concern where none exists.

**10. Escape-a-kill check** — the packet's "KT0 escape" section explicitly cites the exact
scope-note carve-out from `vetoed-decisions.md` (replay-verified / object-type-factored /
cross-game-amortized) and checks the design against all three conditions by name. **✓ Satisfied,
exemplary** — matches the protocol step's intent almost verbatim.

**11. Heretic-before-results** — the packet ends with a ranked "Open questions for the attack"
section, written before any code/results. **✓ Satisfied, exemplary.**

## What this demonstrates

**8 of 11 steps were already independently satisfied**, several by name, in a design written by
someone who had already been through three attacked rounds in the same lineage — real evidence
that the lessons in `failure-catalogue.md` DO transfer forward once learned, and that this skill
mostly formalizes hard-won practice rather than inventing it. **The protocol still surfaces three
concrete, addable gaps the packet's own self-critique (its "open questions for the attack"
section) did not name**: the asymmetric coverage-exclusion denominator between the constructed
and planted arms (step 2), the missing recolor-vs-generic-touched isolation arm (step 3), and the
missing adversarial test of the position-lookup mapper (step 7). None of these are fatal to the
design as written — they are exactly the class of finding a `verified-fable-dispatch.md` attack
pass would likely surface, cheaper, before spending that attack's budget on them.
