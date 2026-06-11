<!-- Reference for the research skill's Output Contract. Loaded on demand.
Consumers: /research (pre-memo gate), /critique verify mode (audit rubric),
/analyze (inference-discipline adjunct). Canonical version — project repos
keep thin instances with their own self-audit tables and point here. -->

# Quantitative Bias Checklist — Pre-Publication Gate

Origin: 2026-06-11 mirror test of the Cato $14.5T fiscal-study criticisms against the research repo's own immigration artifacts (4 hits, none politically directional — the drift is per-claim "favorable construction," not lean). First instance + self-audit table: research-repo `notes/quant-bias-checklist.md`.

**When to run:** before committing any memo, claim register entry, or public artifact where a number does argumentative work, a ranking appears, causal language is used ("caused", "refutes", "explains"), or a welfare/decision conclusion is drawn. A violation means *label the move or downgrade the grade*, not necessarily "don't publish."

**The compressed rule:** every load-bearing number carries its **ledger, unit, base, window justification, gross-or-net status, and measurement-vs-model-output label** — and when several constructions are defensible, the *range across constructions* is the headline, never the favorite endpoint.

**Minimum viable claim** (the object the 32 items inspect): a claim is viable when a stranger, author absent, can (1) **re-derive it** — referent operationally defined, relation + value + unit + base, derivation tagged `measurement|model|inference` with source pointer or regenerating command, assumption stack named if model — and (2) **kill it** — scope stated (ledger, window, population, regime) so in-scope counterexamples count, plus a named defeater (the observation or check that would falsify/supersede). For reuse add a load rating (grade) and lifecycle identity (id, asserted-at, status — substrate `claim.v1` already carries exactly this half). Tier escalation: descriptive = base tuple; causal adds identifying variation + rival-channel status; welfare/policy adds welfare weights or [FRAMING-SENSITIVE]. Most audit failures are a claim missing its tier's field — a descriptive claim wearing causal clothes, a welfare verdict hiding its weights.

Historical anchors are canonical cases [TRAINING-DATA]; verify specifics before citing externally.

## A. Ledger & framing

1. **Ledger switching / equivocation.** Different welfare objects (group A's welfare, aggregate output, per-capita, federal vs local budgets, incumbent vs entrant) treated as one. Anchor: Cato 2026 headlined $14.5T immigrants-alone; the with-US-born-children $7.9T didn't lead. → *Name the ledger in the claim sentence; put the adjacent ledger's number beside the headline.*
2. **Welfare weights hidden.** "Good/bad overall" flips with whose welfare counts; the choice is normative. → *State weights or tag [FRAMING-SENSITIVE].*
3. **Per-what mismatch.** Per-person/household/worker/resident denominators flip signs on the same data. Anchor: Heritage per-household vs NAS per-person; household-weighting correction reordered school-burden rankings (Evidence: research-repo `immigration-household-weighted-correction.md`). → *State the unit; check the source's unit before reuse.*

## B. Counterfactual discipline

4. **Frozen-world counterfactual.** "Without X, outcome = Y" with all behavior, prices, and policy held fixed. Anchors: Cato "debt would be 205% of GDP without immigrants"; the research repo's deportation sim holds replacement hiring at zero. → *List the margins held fixed, or label "mechanical calibration, not forecast."*
5. **Policy endogeneity / Lucas-Goodhart.** Estimates from one regime quoted into another; targeted metrics degrade. Anchor: 1970s Phillips-curve breakdown [TRAINING-DATA]. → *State the identifying variation and refuse extrapolation outside it.*
6. **Static-vs-dynamic accounting conflation.** One-period cash flow and lifetime NPV answer different questions; each is "right" only for its question. → *Say which question the accounting answers.*

## C. Windows, bases, denominators

7. **Window selection.** Start/end dates can manufacture the result. Anchors: Reinhart-Rogoff 90%-debt threshold dissolving under Herndon re-analysis [TRAINING-DATA]; 1998-anchored warming "pause" [TRAINING-DATA]; Cato's 1994-2023 = fastest foreign-born growth window (taxes in-window, entitlement draw outside). → *Justify the window by data constraint explicitly; show one alternative window or say why none exists.*
8. **Low-base percentage.** Big % growth from a small base reads as an explosion. Evidence: research-repo CHNV "+787%" from a 2,598/month base — base present in memo, dropped in the summary layer. → *Every % change carries its absolute base inline.*
9. **Endogenous denominator.** If the denominator responds to treatment, ratios mask load (shelter utilization ratios flat while counts explode). Evidence: research-repo `immigration-receiver-counterfactuals-2026-04-22.md` (Chicago). → *Counts beside ratios whenever the denominator can expand under treatment.*
10. **Gross-for-net substitution.** Gross outlays quoted where the question is net burden (reimbursements, offsets, baseline-anyway spending ignored). Evidence: receiver-city cost table = gross city outlays, federal reimbursements unnetted. → *Say gross or net in the claim; if gross, name the known offsets.*

## D. Aggregation & composition

11. **Simpson's paradox / composition shift.** Aggregate trend reverses within every stratum. Anchors: Berkeley 1973 admissions; pandemic average wages "rising" as low-wage workers exited the denominator [TRAINING-DATA]. → *Check the claim within major strata before publishing the aggregate.*
12. **Ecological fallacy.** Area-level correlation read as person-level fact. Anchor: Robinson 1950 [TRAINING-DATA]. → *Match inference level to data level.*
13. **Average hiding the gradient.** A favorable mean produced by one tail (MI: average immigrant +$10K while subgroups span −$400K to +$1M). → *Report the gradient whenever subgroups plausibly differ in sign.*

## E. Model-output laundering

14. **Model output presented as measurement.** A scalar that exists only inside one assumption stack quoted as observed fact. Anchor: the same 22-year-old HS dropout = −$315K or +$45K under five defensible assumption changes (MI vs Cato WP82). → *Headline the sensitivity range or don't headline the scalar.*
15. **Amplifier add-ons in the preferred direction.** Second-order modeled effects stacked onto first-order estimates, sum headlined. Anchors: Cato's $3.9T interest savings (27% of headline); research-repo 1.6× Type-II multiplier turning $1.45T into $2.32T. → *Lead with first-order; amplified figures only as labeled sensitivity.*
16. **Upper-bound laundering.** Stylized maxima quoted as realistic baselines ("double world GDP"). → *Tag bounds as bounds.*
17. **Shared-cost attribution.** Average-cost vs marginal-cost allocation of public goods/overhead is routinely the single largest swing factor and flips signs (NAS scenarios; in a deficit entity, marginal-cost attribution makes any contributor an "asset"). → *Run or cite both attributions; never present one as "what happened."*

## F. Selection & measurement

18. **Survivorship / attrition.** The sample is the survivors. Anchors: Wald's WWII bomber armor; Secrist 1933 "triumph of mediocrity" [TRAINING-DATA]. → *Ask who exited the sample and why.*
19. **Sample-frame selection.** Anchor: Literary Digest 1936 — 2.4M responses, off by 19 points; N does not cure frame bias [TRAINING-DATA]. → *State the frame.*
20. **Collider conditioning.** Conditioning on a downstream consequence manufactures correlation. Anchor: Berkson's paradox [TRAINING-DATA]; research-repo DAG rule: never condition on apprehension or appearing-in-admin-data. → *Check controls against the DAG; more controls is not monotonically better.*
21. **Construct mismatch.** The measured variable is not the rhetorical category (e.g., "low-skill" operationalized as less-than-HS ≠ "non-college"). → *Define the operational variable next to every category word.*
22. **Silent proxy for the principal.** Exposure/stress proxies read as the welfare object itself (rent exposure ≠ housing welfare loss). → *A proxy is a labeled screen, never the verdict.* (See agent-infra `decisions/2026-06-10-silent-proxy-as-truth.md` for the general rule.)

## G. Inference discipline

23. **Garden of forking paths / p-hacking.** Many undisclosed analyst choices, one published path. Anchors: Simmons et al. 2011; Wansink retractions [TRAINING-DATA]. → *Pre-register the decision rule (/verify-before preregister); disclose paths tried.*
24. **Multiple comparisons.** Anchor: dead-salmon fMRI [TRAINING-DATA]. Positive pattern: 1,000-draw permutation inference (research-repo capacity-falsification pass). → *Permutation/null benchmarks for any scan over many cells.*
25. **Plausibility assertion doing causal work.** "Too large to be anything else" substituting for decomposition. Evidence: research-repo "+4.4pp swing implausibly large for non-immigration causes" — asserted over a near-collinear confound (most-Hispanic counties during a national Hispanic realignment), regression lacking the Hispanic-share control. → *Quantify the rival channel or mark [INFERENCE] and downgrade.*
26. **Spurious time-series correlation.** Trending/nonstationary series correlate by construction. Anchor: Yule 1926 [TRAINING-DATA]. → *Difference, detrend, or design (event study) before claiming co-movement.*
27. **Extrapolation beyond support.** Marginal evidence answering mass-regime questions; in-sample fit answering out-of-distribution policy. Anchors: LTCM 1998; "national house prices never fall" 2008 [TRAINING-DATA]. → *State the support region in the claim itself.*

## H. Publication & process

28. **Headline selection among defensible constructions.** When several constructions are defensible, choosing the favorite as the lead IS the bias — both sides of the Cato dispute did it from the same NAS-family machinery. → *Lead with the range across constructions.*
29. **Advocacy-source laundering.** Numbers acquire false neutrality through citation chains (advocacy-org constructions misattributed to the National Academies). → *Carry provenance tags through every reuse; check the original.*
30. **Reviewer-direction asymmetry.** Hostile audits only for uncongenial conclusions. Mirror-test pattern: audit your own work against the *specific* failure list you just compiled for an adversary — generic "be rigorous" finds nothing; a named list found 4 real hits in one session. → *Run the same-intensity audit on the congenial result (blind first-pass; steel-man both).*
31. **Publication/replication base rates.** Most published effects shrink on replication (Ioannidis 2005; OSC 2015 [TRAINING-DATA]). → *Citation-stance checks (scite contrast); one paper is a hypothesis, not a finding.*
32. **Unlabeled adversarial artifacts.** One-sided briefs are legitimate only when labeled. → *Every artifact states its mode: estimate, bound, screen, or brief.*
33. **Unanchored derived series.** A parsed/derived time series regressed on without checking it against a single externally published value. Evidence: research-repo OHSS parser carried fiscal-index dates AND an agency-block overwrite (series was ports-only, ~5x low) for 7 weeks across 3 ladder claims — one anchor check (Dec 2023 SWB ≈ 302K) caught both in minutes, and the headline finding reversed (2026-06-11 decision record). → *Before the first regression on any built series: verify one known published value, and eyeball one known event (a peak, a collapse) at its calendar date.*

## Mechanically checkable subset (hook candidates on recurrence)

Items 1 (ledger named near headline), 8 (base near any %), 14 (sensitivity range present when "model"/"scenario" appears), 15 (multiplier/amplifier keywords inside headline ranges), 29 (provenance tag present on reused scalars). Don't build the hook until a project shows repeat violations post-checklist — instructions first, architecture on recurrence.
