# DoE failure catalogue — dated, quoted, tagged

Every entry below is a REAL design in the `arc-agi` repo that had a specific, load-bearing defect
found by a frontier attack pass or a builder's own re-derivation. Tags match the numbered steps
in `SKILL.md`. Read the quotes, not just the tag names — the exact language is what makes a
future design checkable against these.

## `rule-privilege-asymmetry`

**Source:** `research/external/2026-07-14-active-goalid-fable-response.md`, active-goalid rung 1
(hypothesis-separation planner design).

> "the shared instrument is broken asymmetrically... grading (a) in the same instrument is fine
> *only* if the instrument is the full sound eliminator for everyone; as written, the 'same
> instrument' claim is false and the gap is partly rule-privilege."

The design believed it graded a passive baseline and a planned-forcing arm under the "same
instrument." It didn't — the elimination rule silently discarded evidence the passive arm's own
behavior generated (BLOCKED-eliminations), so the passive arm was structurally denied credit the
treatment arm could earn. The asymmetry, not the mechanism, produced the apparent gap.

## `negative-control-cannot-pass`

**Source:** `research/external/2026-07-14-active-goalid-fable-response.md`, same rung.

> "A control that always fails is as broken as one that cannot fail... So (a)'s belief at win is
> all switches touched so far — not a singleton unless the walk touched exactly one, which is
> luck (~1/K), not 'expected IDENTIFIED.' The control as specced will report 'whole apparatus
> suspect' every time."

The negative control was specced under a rule that made it structurally incapable of ever
registering a pass, regardless of whether the underlying claim was true. A control incapable of
passing tells you nothing about the treatment — it only tells you the control was mis-specified.

## `zero-context-floor-invalidity`

**Source:** `research/2026-07-14-certificate-gated-distill-design.md` (this session's own probe),
[GPT56-SOL-MAX] attack.

The pilot design sized its "near-ceiling, hard test" framing against a historical corpus rate
(0.886) computed from a DIFFERENT policy's play traces — not this student's own zero-context
baseline. The attack: *"0.886 is not a valid student baseline: it is the historical rate among
already-recorded revision events from another policy. Add a zero-context arm on the same
queries."* When measured directly, this student's own floor was **0.10-0.14**, an order of
magnitude lower — the entire "hard test, little headroom" framing was backwards. Any anchor/floor
borrowed from a different regime must be re-measured on the actual arm before it gates a design.

## `screen-entailed-floor`

**Source:** `research/external/2026-07-14-active-goalid-gametier-fable-response.md`.

> "The passive 0/500 floor is **entailed by the degeneracy screen**, not discovered: you tuned
> hazard columns (1→3→6) until 2000 random actions couldn't succeed, then reported random failing
> at 55 as a finding."

A venue's difficulty parameter was iterated UNTIL the control arm failed, and the control's
subsequent failure was then cited as evidence. This is circular — the "finding" is the tuning
stop-condition restated, not an independent observation.

## `termination-semantics-unstated`

**Source:** `research/external/2026-07-14-active-goalid-gametier-fable-response.md`.

> "The hybrid planner's three headline claims — naive bisection 'permanently stuck,' hybrid
> '6/6,' and the cost table `[30,43,43,30,43,43]` — are **jointly impossible under any single
> termination semantics**; at least one is false, and the pattern points to arms being graded
> under *different* win-termination rules."

Three individually plausible headline numbers turned out to be mutually inconsistent once
termination semantics (when does an episode/attempt end, what persists across attempts) were
checked formally — because the design never pinned them explicitly before code was written,
different arms were silently graded under different implicit rules. The FIX applied one rung
later (`active-goalid-constructedh-packet.md`): **state termination semantics in writing, before
any code, applying uniformly to every arm** — this was explicitly cited as "the fix that a fable
attack had to force me to make explicit last time; doing it before any code is written this
time," and it held on re-attack.

## `scorer-mutation-suite`

**Source:** `research/2026-07-14-certificate-gated-distill-design.md`, `experiments/
cert_distill_probe/scorer_mutation_suite.py`.

> "The scorer must reject the first six [gaming mutations] and accept the last [a known-valid
> repair]. If it cannot, stop: the endpoint is invalid."

A deterministic structural-diff extractor, reused as a "certificate" of non-vacuous change,
was directly tested against 6 adversarial mutations (no-op, unrelated-field change, random-
coordinate padding, hedged disjunction, delete-to-vagueness, evidence-copying) plus 1 known-valid
repair. **It failed 2/6** — it accepted a fabricated unrelated coordinate as a "real" structural
change, and accepted deleting all content down to "unknown, needs more probing" as a "real"
revision (a pure information-loss case scored as a pass). One of the two was fixed cheaply (a
non-vagueness check on the post-side's own content); the other (fabricated-but-well-formed
padding) was left as an acknowledged, unfixed limitation — reported explicitly, not hidden,
rather than claiming a validity the fix didn't achieve.

## `untransported-effect-target`

**Source:** `research/2026-07-14-ratchet-adjudication-math-attack.md`, [GPT56-SOL-MAX] attack.

> "The decisive mistake is treating a `0.12` leaderboard difference as a `0.12` local-RHAE
> difference despite an admitted cross-venue scale mismatch... You implicitly assumed
> `Δ_local = Δ_board = 0.12`. That is the very proposition under dispute."

A power calculation sized a design's decidability against an effect size (a real board-score
gap) measured in a DIFFERENT venue's units than the one being powered — without ever justifying
that the two units transfer 1:1. The same memo had already cited an independent ~52-124× scale
mismatch between the two venues as evidence of *something wrong*, and then used the untransformed
board number as if it were the correct local target in the same breath — an internal
contradiction the design's own author had the evidence for and didn't check. This flipped a
"powered null implies construct-validity gap" headline down to "local-scale equivalence, cross-
venue transport unresolved" — the single most consequential correction of that session.

## `escape-by-assertion-not-observable`

**Source:** `research/external/2026-07-14-active-goalid-fable-response.md`.

> "The *mechanism* arguably escapes; the *experiment as designed* does not demonstrate the
> escape... at K ∈ {4,6} with free door attempts, (c)'s behavior is extensionally 'enumerate a
> small hypothesis set against an outcome oracle' — the Stage-2 kill's silhouette... The escape
> becomes *empirical* rather than asserted only when the venue contains pressure that separates
> planned forcing from both naive activity and passive accumulation."

A design argued in prose that its mechanism was structurally different from a previously-killed
approach — but under the stated parameters, its OBSERVABLE behavior was indistinguishable from
the killed mechanism wearing a different name. An "escape" claim needs a named observable that
would fire if the escape were illusory, checked, not just an argument that the mechanisms are
conceptually different.

## `merge-inference-not-computed`

**Source:** `research/external/2026-07-14-active-goalid-fable-response.md`, same dispatch.

> "The correct construction is to *compute* the partition rather than infer it: mutual
> inseparability over the reachable-touched-set family is an equivalence relation by
> construction... A merge without a BFS witness naming the specific unreachable-without-i
> candidate is not a merge; it is an unexplained infeasibility and must halt-and-report."

Where a design INFERS a structural property (an equivalence class, a partition, a merge
decision) from observed FAILURES of a heuristic test, rather than computing it directly from the
generative model, the inference can be non-transitive, order-dependent, and conflate two
different failure causes (logical impossibility vs. mere budget exhaustion). Wherever a ground-
truth computation is available at the design's scale, prefer computing the property directly and
use the heuristic only as something to be VALIDATED against that computation, not the primary
source of truth.

## `reset-semantics-unspecified`

**Source:** `research/external/2026-07-14-active-goalid-fable-response.md`.

> "Nothing in the packet says episodes reset between (c)'s routes. If state persists and
> bookkeeping uses per-route touched-sets, every post-win exit attempt returns OPEN and (c)
> 'discards' whichever candidate it omitted each round — collapsing to an order-dependent,
> usually wrong singleton."

A sibling of `termination-semantics-unstated`: specifically, whether STATE (not just the episode
attempt count) persists or resets between trials/attempts must be stated, because silent
persistence can make bookkeeping order-dependent in a way that looks like a clean result but
isn't reproducible under a different trial order.

## `elimination-on-intent-not-realized-effect`

**Source:** `research/external/2026-07-14-active-goalid-gametier-packet.md` / blind draft, self-
caught before the attack.

> "Elimination on the intended target instead of the ACTUAL touched-set a route produces... use
> the route's REAL resulting touched-set, never the naively-intended target."

A planner's credit/elimination bookkeeping was written to use what an action route was SUPPOSED
to touch, rather than what it ACTUALLY touched when executed — a design-vs-realization gap that,
left unchecked, silently corrupts every downstream belief-update computed from it.

## `fixed-wall-as-cost-ceiling`

**Source:** operator feedback, 2026-07-16, during the microscale-Mealy direct-K ceiling sequence;
measured parent runs completed in 221 seconds under a 1,200-second breaker and 111 seconds under a
600-second breaker.

> "Cost ceiling: 1 local CPU × ≤600 s × $0/hr = $0 external — this should be more dynamic ...
> might be counterproductive rule tbh"

A fixed wall was being repeated as a "cost ceiling" even though local CPU external spend was
exactly zero. The number protected against hangs, not cost, but its scientific placement could
invalidate a progressing run under transient contention and encourage ritual reuse of 240/600/
1,200-second constants. The repair is to type the controls: hard circuit breaker for external
spend; measured expected runtime plus a derived, preferably progress-aware stall watchdog for `$0`
local work. A watchdog kill is runtime invalidity, never evidence that the mechanism lacks
capacity.
