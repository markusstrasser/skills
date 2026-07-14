# Classical DoE canon — short pass, mapped to our failure classes

Not a survey. Each citation below is here because it formally backs a specific entry in
`failure-catalogue.md` — read it when that failure class is live in a design, not as background
reading. Sourced via the research MCP (Semantic Scholar), titles/authors/years/citation-counts
verified at fetch time (2026-07-14); abstracts not independently fetched beyond the search
snippet — treat mechanism claims below as scout-level, verify primary text before a load-bearing
citation in a memo.

## Fisher's three principles — replication, randomization, blocking

**[SOURCE]** J. Box, "R.A. Fisher and the Design of Experiments, 1922–1926," *The American
Statistician* (1980), 126 citations. Historical primary account of Fisher's original three
principles at Rothamsted: **replication** (repeat under the same conditions to estimate error),
**randomization** (assign treatments by chance so unmeasured confounds don't systematically favor
one arm — the formal backstop for `rule-privilege-asymmetry`: if arm assignment itself, not just
grading, is confound-free by construction, an asymmetric instrument has less room to hide), and
**blocking** (group units by a known nuisance factor, e.g. field plot, so it doesn't inflate
treatment variance — the classical analogue of `screen-entailed-floor`'s fix: block on the
difficulty-tuning knob rather than letting it silently vary between the calibration run and the
measurement run).

**Factorial vs. one-factor-at-a-time (OFAT):** a full or fractional factorial design varies
multiple factors simultaneously and can detect INTERACTIONS between them at the same total cost
OFAT spends detecting main effects alone — directly relevant whenever a design's SHAM ladder (§3
in SKILL.md) is testing multiple components (gating × read-back × content): a factorial layout
over those components, not a sequence of one-at-a-time shams, is the textbook-correct design when
budget allows it, because OFAT cannot detect that two components only matter TOGETHER.

**[SOURCE]** Kuehl, *Design of Experiments: Statistical Principles of Research Design and
Analysis* (1999), 858 citations — the standard modern textbook reference for the full factorial/
blocking/randomization apparatus, if a design needs more than the summary above.

## TOST — equivalence testing, not "failure to reject"

**[SOURCE]** D. Schuirmann, "A comparison of the Two One-Sided Tests Procedure and the Power
Approach for assessing the equivalence of average bioavailability," *J. Pharmacokinetics and
Biopharmaceutics* (1987), 2049 citations. The original TOST paper. **The formal backstop for
step 8's equivalence-test requirement**: a non-significant difference test does NOT establish
equivalence (it establishes only "not enough power to see a difference," which is exactly the
`zero-context-floor-invalidity` and general underpowering failure mode this catalogue keeps
finding). TOST instead runs two one-sided tests against a PRE-REGISTERED margin `±δ`; equivalence
is concluded only if BOTH one-sided nulls (difference ≥ +δ, difference ≤ −δ) are rejected — i.e.
the confidence interval on the difference falls entirely inside `[−δ, +δ]`. Any design in this
project claiming "no effect" from a null result should be restated as a TOST claim with a stated
margin, or explicitly flagged as underpowered rather than equivalent.

**[SOURCE]** C. Lauzon, B. Caffo, "Easy Multiplicity Control in Equivalence Testing Using Two
One-sided Tests," *The American Statistician* (2009), 60 citations. Practical multiplicity
correction for TOST when running several equivalence tests at once (e.g. per-arm or per-stratum)
— relevant whenever a design's bands (step 8) are evaluated across multiple sub-populations and
naive per-test alpha would inflate the false-equivalence rate.

## Sequential and optimal design

`loop/seq_stop.py` (see `house-rules.md`) already implements Wald SPRT and O'Brien-Fleming
group-sequential boundaries in-repo — use those directly rather than re-deriving. For the
broader modern framing:

**[SOURCE]** X. Huan, J. Jagalur, Y. Marzouk, "Optimal experimental design: Formulations and
computations," *Acta Numerica* (2024), 116 citations. Modern systematic treatment of "how best to
acquire data" as a formal optimization over the design space — relevant when a design has a
continuous or high-cardinality choice of WHERE to sample next (which held-out games, which
context-exemplar count) rather than a fixed small arm set; the Bayesian-optimal-design framing
generalizes the "run the cheapest, most-damning sham first" heuristic (SHAM-0 in step 3) into a
formal expected-information-gain ordering when there are more than 3-4 candidate next probes to
choose among.

## What classical DoE does NOT cover (why the catalogue is still primary)

None of the above formally addresses: rule-privilege asymmetry between differently-instrumented
arms, termination-semantics consistency across arms in an interactive/episodic setting, mechanical
verifier gaming (the mutation-suite discipline), or cross-venue effect-size transport — these are
failure modes specific to interactive, LLM-agent, multi-instrument measurement in a way 20th-
century field-trial DoE never had to consider. The catalogue is the primary evidence base for a
reason; classical DoE supplies vocabulary and a few formal tools (TOST, factorial layouts,
sequential boundaries) that slot into specific steps, not a replacement design philosophy.
