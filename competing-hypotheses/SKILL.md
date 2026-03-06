---
name: competing-hypotheses
description: "Analysis of Competing Hypotheses (ACH). Use when investigating any entity, anomaly, root cause, or claim that could have multiple explanations -- fraud vs error, bug vs design, correlation vs causation. Based on Richards Heuer's CIA methodology, formalized with Bayesian LLR scoring."
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

- Data source access (DuckDB, SQL, APIs — whatever the project uses)
- ACH scoring tool if available (`ach_scorer.py` or equivalent). Manual matrix scoring works too.
- Base rates for the domain if available (project's `priors.md` or equivalent)

For reasoning principles referenced throughout, read `references/` in the `causal-check` skill.

## Phase 1: Constructive Abduction

1. **State the observation** in one sentence.
2. **Characterize observation geometry** — what shape does the pattern have?
   - **Sharp break** (abrupt level change, sudden onset/cessation) → at least one hypothesis MUST be a discrete event (policy change, regulatory action, leadership change, product launch/failure)
   - **Gradual erosion/drift** (multi-year trend, slow decay) → at least one hypothesis MUST be structural (competitive displacement, demographic shift, technology substitution)
   - **Isolated cluster** (specific entities/region, not sector-wide) → at least one hypothesis MUST be entity-specific (fraud, local regulation, management)
   - **Sudden absence** (metric drops to zero, activity ceases) → at least one hypothesis MUST be a termination event (enforcement, bankruptcy, data collection change)
   - **Oscillating/cyclical** → consider capital cycle, seasonal, or regulatory cycle hypotheses
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

**Assign prior probabilities** from base rates or domain knowledge. Must sum to 1.0.

## Phase 3: Predict Data Footprints (BEFORE querying)

For EACH hypothesis, predict what data footprint it would leave if true. This is the critical step — predictions BEFORE data prevent confirmation bias.

Write predictions in a table:

| Evidence | If H1 | If H2 | If H3 |
|----------|-------|-------|-------|
| Metric A | Expected value | Expected value | Expected value |
| Metric B | Expected value | Expected value | Expected value |

For each cell, assign P(evidence | hypothesis) as a number in (0, 1).
These are LIKELIHOODS, not posteriors. They answer: "If this hypothesis were true, how likely would we see this evidence?"

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

Score hypotheses using Bayesian updating. If `ach_scorer.py` is available:

```python
from tools.lib.ach_scorer import ACHMatrix

m = ACHMatrix(
    hypotheses=["h1", "h2", "h3"],
    priors=[0.40, 0.30, 0.30],
)
m.add_evidence("metric_a", [0.80, 0.20, 0.05])
m.add_evidence("metric_b", [0.85, 0.15, 0.02])

result = m.score()
print(m.format_matrix(result))
```

Otherwise, compute manually: posterior ∝ prior × Π(likelihoods). Normalize.

**Interpret the output:**
- **Posteriors**: updated probabilities after evidence
- **Diagnosticity**: which evidence most differentiates hypotheses (focus investigation here)
- **Inconsistency scores**: Heuer's method — most negative = most inconsistent = REJECT
- **Separation**: log-odds gap between top two hypotheses. >1.0 = strong, <0.5 = inconclusive

## Phase 5b: Inference to Best Explanation (IBE) Scoring

After Bayesian scoring, apply explanatory quality criteria. Bayesian LLR tells you which hypothesis is most consistent with evidence; IBE tells you which is the BEST explanation.

For each surviving hypothesis (posterior > 0.10), score on 5 dimensions:

| Criterion | Question | Score 1-5 |
|-----------|----------|-----------|
| **Explanatory scope** | How many of the observations does this hypothesis explain? (not just "consistent with" — actively explains) | |
| **Specificity** | Does this hypothesis predict the EXACT pattern observed, or just "something like it"? | |
| **Parsimony** | How many independent assumptions does this hypothesis require? Fewer = better. | |
| **Unification** | Does this hypothesis connect previously unrelated observations? | |
| **Fertility** | What NEW testable predictions does this hypothesis generate? More = better. | |

**Scoring rules:**
- A hypothesis that explains 8/10 observations specifically scores higher than one that is "consistent with" all 10 vaguely
- A hypothesis requiring 2 assumptions beats one requiring 5, even if the 5-assumption version fits slightly better
- **Fertility is the tiebreaker.** If two hypotheses score similarly, the one that predicts more NEW checkable things wins — it's more falsifiable, which means it's more informative

**Output format:**
```
IBE Scoring:
  H1 (measurement surface): scope=4, specificity=4, parsimony=3, unification=5, fertility=4 → IBE=20
  H2 (latent g gap):        scope=3, specificity=2, parsimony=4, unification=2, fertility=2 → IBE=13
  H3 (school pipeline):     scope=3, specificity=3, parsimony=3, unification=3, fertility=3 → IBE=15
```

**Integration with Bayesian scoring:** IBE does NOT override posteriors. It supplements them. If Bayesian posterior says H1=0.45, H2=0.35, and IBE says H1 is also the best explanation, that's converging evidence. If they disagree (high posterior but poor explanation), flag for investigation — the hypothesis may be fitting noise.

## Phase 6: Kill or Promote

Based on the ACH result:

1. **Kill hypotheses** with posterior < 0.05 or inconsistency score in the bottom quartile. State WHY they died (which evidence killed them).
2. **Flag inconclusive** if separation < 0.5 between top two. Identify what additional evidence would resolve the ambiguity.
3. **Promote surviving hypothesis** if separation > 1.0 and posterior > 0.50.

## Phase 7: Write the Report

Structure the output with:
- Question framing (from Phase 1)
- ACH Matrix (from Phase 5)
- Evidence summary table: #, Evidence, Finding, Most Supports, Source
- Verdict: Surviving hypothesis (posterior), Killed hypotheses (why), Next steps

## Methodology Notes

- **Shape-match your hypotheses to the observation.** Phase 1 geometry constrains what hypotheses are admissible. If all your hypotheses have the wrong shape, you'll find the "best" wrong answer.
- **Heuer's key insight: focus on inconsistency, not confirmation.** The most diagnostic evidence is what DIFFERENTIATES hypotheses, not what supports all of them equally.
- **Always include "data artifact" as a hypothesis.** What looks like a real pattern can be shared exposure to the same external driver.
- **Correlated evidence inflates posteriors.** If multiple signals come from the same underlying cause, collapse them into one composite feature or use covariance-aware combination.
- **Absence of expected evidence is itself evidence.** If H1 predicts X and you find nothing, that's evidence AGAINST H1.
- **Prior sensitivity check.** If the verdict changes when you double or halve the prior for the leading hypothesis, the evidence is too weak to conclude.
- **Do NOT stop at the ACH matrix.** The matrix identifies the surviving hypothesis and the most diagnostic evidence. The NEXT step is to go gather more of that diagnostic evidence. ACH directs investigation, not concludes it.
- **Multi-cause is allowed when each cause has independent, non-overlapping fingerprints.** Don't force single-cause commitment. But "six gradual factors" with no independent evidence for each is factor-listing, not explanation.
