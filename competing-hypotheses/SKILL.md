---
name: competing-hypotheses
description: "Analysis of Competing Hypotheses (ACH). Use when investigating any entity, anomaly, root cause, or claim that could have multiple explanations -- fraud vs error, bug vs design, correlation vs causation. Based on Richards Heuer's CIA methodology, formalized with Bayesian LLR scoring."
effort: high
---

# Analysis of Competing Hypotheses

Invocation: `/competing-hypotheses SUBJECT`

Where SUBJECT is an entity name, ticker, anomaly description, or claim to evaluate.

## When to Use

- Any lead >$10M (MANDATORY per project constitution, if applicable)
- Any anomaly that could be fraud, error, OR legitimate outlier
- Correlation claims that need causal evaluation
- Investment theses with competing bull/bear narratives
- Any time you catch yourself with a single explanation

## Prerequisites

- Data source access (DuckDB, SQL, APIs -- whatever the project uses)
- ACH scoring tool if available (`ach_scorer.py` or equivalent). Manual matrix scoring works too.
- Base rates for the domain if available (project's `priors.md` or equivalent)

For reasoning principles referenced throughout, read `references/` in the `causal-check` skill.

## Phase 1: Constructive Abduction

1. **State the observation** in one sentence.
2. **Characterize observation geometry** -- what shape does the pattern have?
   - **Sharp break** (abrupt level change, sudden onset/cessation) -> at least one hypothesis MUST be a discrete event (policy change, regulatory action, leadership change, product launch/failure)
   - **Gradual erosion/drift** (multi-year trend, slow decay) -> at least one hypothesis MUST be structural (competitive displacement, demographic shift, technology substitution)
   - **Isolated cluster** (specific entities/region, not sector-wide) -> at least one hypothesis MUST be entity-specific (fraud, local regulation, management)
   - **Sudden absence** (metric drops to zero, activity ceases) -> at least one hypothesis MUST be a termination event (enforcement, bankruptcy, data collection change)
   - **Oscillating/cyclical** -> consider capital cycle, seasonal, or regulatory cycle hypotheses
3. **Define the null generative process.** What baseline explains the observation without any special cause? (Market trend, macro growth, population change, random walk.)
4. **Check for lagged causes.** The cause may precede the observed effect by months or years. Don't restrict hypothesis search to coincident events.
5. **Identify the domain:** fraud detection, investment, regulatory, or mixed.
6. **Fetch base rates** for this domain if available.

**Shape-match your hypotheses to the observation.** A sharp break demands at least one discrete-event hypothesis. A gradual decline demands at least one structural hypothesis. Mismatched shapes are a red flag.

**Output:** Write the framing before proceeding. Example:
> **Observation:** [quantified one-sentence pattern]
> **Geometry:** [sharp break / gradual / cluster / absence / cyclical]
> **Null process:** [baseline explanation]
> **Domain:** [fraud / investment / regulatory / mixed]
> **Base rate:** [from available data or domain knowledge]

## Phase 2: Generate Hypotheses

Generate MINIMUM 3 competing hypotheses. Always include:

1. **The lead hypothesis** (what you suspect)
2. **Benign coincidence** (innocent explanation)
3. **Data artifact** (the signal is noise, measurement error, or methodology flaw)

For fraud investigations, also consider:
4. **Error** (incompetence, not intent)
5. **Regulatory arbitrage** (legal but exploitative)

For investment theses, also consider:
4. **Already priced in** (market knows this)
5. **Structural rather than temporary** (the anomaly IS the new normal)

**Independence check (denial prompting):** After generating H1, state its core mechanism in one sentence. Then generate H2 under the constraint: "Explain the observation WITHOUT {H1's mechanism}." Repeat for H3. If you can't generate a hypothesis without H1's mechanism, note it -- that's evidence H1 is strongly supported. Hypotheses that share a core mechanism aren't truly competing; they're variations.

**Assign prior probabilities** from base rates or domain knowledge. Must sum to 1.0.

## Phase 3: Predict Data Footprints (BEFORE querying)

For EACH hypothesis, predict what data footprint it would leave if true. This is the critical step -- predictions BEFORE data prevent confirmation bias.

Write predictions in a table. For each cell, assign P(evidence | hypothesis) in (0, 1). These are LIKELIHOODS, not posteriors: "If this hypothesis were true, how likely would we see this evidence?"

See `references/evidence-matrix-template.md` for the table format.

**Diagnosticity focus:** Prioritize predictions that DISTINGUISH hypotheses -- evidence items where the likelihood varies widely across hypotheses. Evidence consistent with all hypotheses equally is confirmatory but not diagnostic.

## Phase 4: Gather Evidence

Query your data sources to test each prediction.

**Rules:**
- Query ONE evidence item at a time
- Record what you actually find, not what you expected
- If a query returns zero rows, that IS evidence (absence can be diagnostic)
- Source-grade every finding: `[DATA]` for your analysis, Admiralty for external

**For each evidence item:**
1. Write the query
2. Execute it
3. Record the actual result
4. Compare to your predictions from Phase 3
5. Assign final likelihood values based on what you found

## Phase 5: Score the Matrix

Score hypotheses using Bayesian updating. See `references/ach-scorer-example.md` for the Python API and manual computation method.

**Interpret the output:**
- **Posteriors**: updated probabilities after evidence
- **Diagnosticity**: which evidence most differentiates hypotheses (focus investigation here)
- **Inconsistency scores**: Heuer's method -- most negative = most inconsistent = REJECT
- **Separation**: log-odds gap between top two hypotheses. >1.0 = strong, <0.5 = inconclusive

## Phase 5b: Inference to Best Explanation (IBE)

After Bayesian scoring, apply explanatory quality criteria. Bayesian LLR tells you which hypothesis is most consistent with evidence; IBE tells you which is the BEST explanation.

For each surviving hypothesis (posterior > 0.10), use **pairwise dominance comparison** on 5 dimensions: explanatory scope, specificity, parsimony, unification, fertility. See `references/ibe-dominance-format.md` for criteria definitions, dominance rules, and output format.

**Fertility is the tiebreaker.** When tradeoffs are close, the hypothesis generating more NEW checkable predictions wins -- it's more falsifiable.

## Phase 5c: Falsification Queries

For each surviving hypothesis (posterior > 0.10, not yet killed):

1. **Generate measurable implications.** Ask: "If H is true, what specific, observable evidence SHOULD exist that we haven't checked yet?" Generate 2-3 implications per hypothesis.
2. **Relevance check.** Discard implications that would hold under multiple hypotheses (low diagnosticity). Only keep implications that distinguish this hypothesis from competitors.
3. **Execute falsification searches.** Record what you found AND what you didn't find (pertinent negatives). Source-grade each finding.
4. **Update the ACH matrix.** Rescore using the same Bayesian method as Phase 5.
5. **Termination.** Stop when: (a) one hypothesis dominates on diagnosticity-weighted evidence, OR (b) you've exhausted 3 rounds of falsification without convergence (flag as genuinely ambiguous).

**When to skip:** If the hypothesis space is narrow (2 hypotheses, both well-evidenced) and additional searching is unlikely to be diagnostic, skip directly to Phase 6.

**Statistical rigor note:** In data-rich domains where falsification experiments can produce p-values, use sequential testing (see POPPER framework, arXiv:2502.09858). In qualitative domains (OSINT, intelligence analysis), falsification queries produce directional evidence, not statistical proof. State this explicitly in the report.

## Phase 6: Kill or Promote

1. **Kill hypotheses** with posterior < 0.05 or inconsistency score in the bottom quartile. State WHY they died (which evidence killed them).
2. **Flag inconclusive** if separation < 0.5 between top two. Identify what additional evidence would resolve the ambiguity.
3. **Promote surviving hypothesis** if separation > 1.0 and posterior > 0.50.

## Phase 7: Write the Report

See `references/evidence-matrix-template.md` for report structure and evidence summary table format.

## Anti-Patterns

- **Shape mismatch.** Phase 1 geometry constrains what hypotheses are admissible. If all your hypotheses have the wrong shape, you'll find the "best" wrong answer.
- **Confirmation over diagnosticity.** Heuer's key insight: focus on inconsistency, not confirmation. The most diagnostic evidence DIFFERENTIATES hypotheses, not supports all of them equally.
- **Missing "data artifact" hypothesis.** What looks like a real pattern can be shared exposure to the same external driver.
- **Correlated evidence inflating posteriors.** If multiple signals come from the same underlying cause, collapse them into one composite feature or use covariance-aware combination.
- **Ignoring absence.** Absence of expected evidence is itself evidence. If H1 predicts X and you find nothing, that's evidence AGAINST H1.
- **Prior sensitivity.** If the verdict changes when you double or halve the prior for the leading hypothesis, the evidence is too weak to conclude.
- **Stopping at the matrix.** The matrix identifies the surviving hypothesis and the most diagnostic evidence. The NEXT step is to go gather more of that diagnostic evidence. ACH directs investigation, not concludes it.
- **Forcing single-cause.** Multi-cause is allowed when each cause has independent, non-overlapping fingerprints. But "six gradual factors" with no independent evidence for each is factor-listing, not explanation.
