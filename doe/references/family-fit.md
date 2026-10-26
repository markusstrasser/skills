# /doe scope and family-fit rationale

<!-- moved-from doe/SKILL.md L12-92 2026-10-26 -->
## Scope and family fit (/doe vs /eval) (moved verbatim from SKILL.md)

> Moved verbatim from doe/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

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
