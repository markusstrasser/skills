---
name: analyze
description: "Reasoning frameworks — causal inference, DAG construction, sensitivity analysis, competing hypotheses (ACH), forensic investigation. All local analysis, no external dispatch."
user-invocable: true
argument-hint: <mode> [question or target]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: high
---

# Analyze

Unified reasoning and investigation skill. Five modes, one entry point.

**Invocation:** `/analyze <mode> [question or target]`

## Mode Selection

| Mode | Triggers on | Use when |
|------|-------------|----------|
| **causal** (default for "why") | "why did", "what caused", "root cause", "explain the decline/rise/change" | Any "why" question about an observed pattern |
| **dag** | "regression", "control for", "adjust for", "covariate", "confound", "causal effect of X on Y" | Before specifying any regression model |
| **robustness** | After fitting OLS model from dag mode | Quantifying sensitivity to unmeasured confounding |
| **hypotheses** | Competing explanations, fraud vs error, anomaly with multiple explanations | Entity investigation, anomaly with 3+ explanations, leads >$10M |
| **investigate** | "find fraud", "audit", "follow the money", "OSINT", "shell companies" | Forensic deep-dive on datasets, entities, or systems |

**Pipeline suggestion:** `dag` -> `robustness` (auto-suggest after DAG specification produces a fitted model).

---

## Mode: causal

Causal inference discipline for "why" questions. Enforces explanatory specificity: match explanation shape to observation shape, define the null, predict new footprints, commit probabilistically. Prevents factor-listing and narrative-plausible-but-causally-wrong explanations.

For full reasoning principles, read `references/reasoning-principles.md`.

### Phase 0: Characterize Observation

1. **State the observation** in one precise sentence with numbers. "Revenue declined" is not an observation. "Revenue declined 34% YoY in Q3 2025" is.

2. **Define the null generative process.** What baseline explains this observation without any special cause?
   - Market/sector trend (SPY up 20%, sector down 15%)
   - Random walk / mean reversion from prior extreme
   - Macro cycle (rate environment, GDP growth, seasonal)
   - Population/demographic base rate change

   If the null explains the observation, STOP. The answer is "nothing unusual happened." Detrending first (Brooklyn lesson: r=0.86 -> 0.038).

3. **Characterize the residual geometry** (after removing the null):
   - **Sharp break** -- abrupt level change at identifiable date
   - **Gradual erosion** -- multi-year trend, no single inflection
   - **Isolated cluster** -- affects specific entities/regions, not the class
   - **Sudden absence** -- metric drops to zero or near-zero
   - **Oscillating/cyclical** -- recurring pattern with period

4. **Check for lagged causes.** The cause may precede the effect by months/years. Regulatory changes, capital cycles (2-5 year lag). Don't restrict search to coincident events.

5. **Quantify the magnitude.** What's the effect size? Is it within normal variance or 2+ sigma?

**Output format:**
> **Observation:** [precise, quantified]
> **Null:** [baseline explanation]
> **Residual after null:** [what remains unexplained]
> **Geometry:** [sharp break / gradual / cluster / absence / cyclical]
> **Magnitude:** [effect size, sigma from norm]
> **Lag window:** [how far back to search for causes]

### Verification Gate

Before generating hypotheses, verify:
1. **Residual geometry check:** Is the shape classification correct?
2. **Null adequacy:** Have you defined the null process? If the null fully explains the observation, stop.
3. **Magnitude sanity:** Is the effect size actually outside normal variance?

If any check fails, revise Phase 0 before proceeding.

### Phase 1: Generate Shape-Constrained Hypotheses

Generate 3-5 candidate explanations. Constrained by geometry:

| Geometry | MUST include | SHOULD include |
|----------|-------------|----------------|
| Sharp break | Discrete event (policy, leadership, product, enforcement) | Threshold/tipping point of gradual process |
| Gradual erosion | Structural shift (competition, demographics, technology) | Multiple compounding structural factors |
| Isolated cluster | Entity-specific cause (management, local regulation, fraud) | Selection/survivorship artifact |
| Sudden absence | Termination event (enforcement, bankruptcy, data change) | Measurement/reporting change |
| Oscillating | Cyclical driver (capital cycle, seasonal, regulatory) | Resonance between multiple cycles |

**Always include:** "Data artifact / measurement change" -- the observation itself might be wrong.

**Multi-cause allowed** when each cause has independent, non-overlapping fingerprints.

**Assign prior probabilities.** Must sum to 1.0.

### Phase 2: Seek Natural Experiment

Look for natural experiments that discriminate between hypotheses:
- **Cross-sectional variation:** Did the effect hit everyone, or only a subgroup?
- **Temporal variation:** Does the effect start at a specific date?
- **Geographic/regulatory variation:** Different jurisdictions -> different outcomes?
- **Dose-response:** Entities more exposed should show larger effects.

If no natural experiment exists, note this as an epistemic limitation.

### Phase 3: Specificity Ranking

For each surviving hypothesis, evaluate:
1. **Temporal specificity:** Does the cause's timing match the effect's onset?
2. **Magnitude specificity:** Does the cause's expected effect size match?
3. **Scope specificity:** Does the cause predict the right affected population?
4. **Mechanism specificity:** Can you trace the causal chain step-by-step?

**Anti-overfit test:** For the leading hypothesis, predict at least one NEW footprint you haven't checked yet. Go check. If it fails, downgrade.

**Score each hypothesis:**
| Hypothesis | Temporal | Magnitude | Scope | Mechanism | New prediction | Total |
|-----------|----------|-----------|-------|-----------|---------------|-------|

### Phase 3b: Recursive Causal Audit (RCA)

Before committing, verify each surviving hypothesis step-by-step.

For the top 2 hypotheses, trace the causal chain:

**Step 1 -- Mechanism chain:** Write each link explicitly.
```
H1: A -> B -> C -> D
     [type]  [type]  [type]  [type]
```

**Step 2 -- Link-by-link audit:** For each link:
- Is this link **directional** (A causes B, not just correlated)?
- Is this link **necessary** (without A, would B still happen)?
- Is this link **proportional** (does the size of A predict the size of B)?
- Could there be a **confounder** between A and B?
- Is any variable a **descendant** of the treatment? (collider bias risk)

**Step 3 -- Identify the weakest link.** Focus next investigation here.

**Step 4 -- Check for bad controls.** If regression involved:
- List every control variable
- For each: is it pre-treatment, post-treatment, or descendant of treatment?
- Any descendant of treatment used as a control is a bad control -- flag immediately
- For complex models, switch to `dag` mode for full DAG validation

### Phase 4: Commit or Escalate

**If one hypothesis dominates** (specificity score 2x+ the next):
> **Most likely cause (X%):** [hypothesis] -- [one-sentence mechanism]
> **Top alternative (Y%):** [hypothesis] -- [why it's less specific]
> **Falsifier:** [what evidence would disprove the leading hypothesis]
> **Decision impact:** [how this conclusion affects decisions]

**If two hypotheses are close** (within 1.5x specificity):
> **Inconclusive between:** [H1] and [H2]
> **Discriminating evidence needed:** [what data would separate them]

**If no hypothesis fits well:**
> **Honest answer:** The available evidence doesn't support a confident causal attribution.

### Output Requirements (causal mode)

Every causal analysis MUST include:
1. **P(cause)** -- probability assigned to the leading explanation
2. **Top alternative** -- the second-best explanation and why it's less specific
3. **Falsifier** -- what would disprove the leading explanation
4. **Decision impact** -- what changes if the leading explanation is right vs. wrong

---

## Mode: dag

DAG-first causal analysis. Forces directed acyclic graph construction and back-door criterion validation before any regression specification. Prevents bad-control, collider bias, and M-bias.

See `references/dag-construction.md` for the 4-stage decomposition procedure and Meek rules. See `references/adjustment-algorithms.md` for the back-door criterion procedure. See `references/output-templates.md` for specification template and consensus mode. See `references/worked-example.md` for a bad-control trap walkthrough.

### Phase 1: Variable Classification

For every variable, classify it:

| Variable | Classification | Temporal Order | Justification |
|----------|---------------|----------------|---------------|
| ... | Treatment (X) | ... | ... |
| ... | Outcome (Y) | ... | ... |
| ... | Pre-treatment confounder (C) | Before X | Causes both X and Y because... |
| ... | Mediator (M) | Between X and Y | On causal path X -> M -> Y |
| ... | Descendant of treatment (D) | After X | Caused by X, do NOT control |
| ... | Descendant of outcome | After Y | Caused by Y |
| ... | Instrument (Z) | Before X | Causes X but not Y directly |
| ... | Collider | Varies | Caused by two+ variables -- conditioning opens spurious path |

**Gate:** Every variable classified into exactly one role. Plausible alternatives listed. Each confounder must cause BOTH treatment and outcome.

### Phase 2: Construct the DAG (4-stage decomposition)

Build in four stages: skeleton, V-structures, Meek rules, flag undirected. See `references/dag-construction.md`.

**Gate:** Temporal defensibility of every edge. Missing edges are claims of no relationship. All colliders intentional. No cycles.

### Phase 3: Identify Adjustment Set

Find set S satisfying the back-door criterion. See `references/adjustment-algorithms.md`.

**Do NOT include:** mediators, descendants of treatment, descendants of outcome, colliders on non-causal paths.

### Phase 4: Bad-Control Audit

For EACH variable in the proposed regression:

| Variable | In DAG? | Classification | In valid adjustment set? | Problem? |

**Trap catalog -- if any fires, STOP:**

| Pattern | Flag | What goes wrong |
|---------|------|-----------------|
| Descendant of X as control | **OVER-CONTROL / COLLIDER BIAS** | Blocks causal effect or opens spurious path |
| Mediator as control | **OVER-CONTROL** | Blocks X -> M -> Y |
| Variable not in DAG | **UNJUSTIFIED** | No causal story |
| Collider conditioned on | **SPURIOUS PATH OPENED** | Opens non-causal path between parents |
| Post-treatment variable | **POST-TREATMENT BIAS** | Can be affected through unmeasured paths |

### Phase 5: Specification Output

Only after Phases 1-4 pass clean. See `references/output-templates.md`.

### Output Requirements (dag mode)

Every dag analysis MUST produce:
1. Variable classification table
2. DAG in text notation
3. Valid adjustment set with exclusions and reasons
4. Bad-control audit table
5. Clean regression specification -- or a STOP with what needs fixing
6. Remaining assumptions and threats

### Common Traps

1. **"Just control for everything available."** Each control is a causal claim.
2. **"More controls = less bias."** False for descendants and colliders.
3. **"The reviewer asked us to control for X."** Check the DAG. Reviewers can be wrong.
4. **"It's a covariate, not a control."** If it's in the conditioning set, it adjusts the estimate.
5. **"We're just being conservative."** Including a collider introduces bias.
6. **"The coefficient changed when we added Z, so Z must be a confounder."** If Z is a collider, the change is bias being introduced.

**After completing dag mode and fitting a model, consider running `robustness` mode for sensitivity analysis.**

---

## Mode: robustness

Post-estimation sensitivity analysis. Quantifies how robust a causal estimate is to unmeasured confounding using PySensemakr (Cinelli-Hazlett OVB framework). Use AFTER fitting an OLS model (typically after dag mode).

**When NOT to use:** Before model fitting. For non-OLS models (logit, etc.) -- PySensemakr assumes linear models.

### Steps

1. Provide the fitted model formula + data path
2. Run sensitivity analysis:
```bash
uv run --with PySensemakr python3 sensitivity_check.py \
  --formula "Y ~ X + C1 + C2" \
  --data "path/to/data.csv" \
  --treatment "X" \
  --benchmark "C1,C2"
```
3. Benchmarks against observed covariates
4. Interpretation: how strong would an omitted confounder need to be?

### Interpretation Guide

The Robustness Value (RV) represents the minimum strength of association (partial R-squared) an omitted confounder would need to have with BOTH treatment AND outcome to explain away the estimated effect. Benchmarking uses `sensemakr.ovb_bounds()` (2D: partial R-squared with treatment AND outcome).

- **RV > 2x strongest benchmark** -- robust. Omitted confounder would need >2x the strongest observed covariate.
- **1x < RV < 2x** -- moderate. Note limitation in write-up.
- **RV < 1x** -- fragile. Revisit DAG for missing confounders before trusting the estimate.

### Output

```json
{
  "treatment": "X",
  "estimate": 0.34,
  "robustness_value": 0.42,
  "rv_alpha": 0.31,
  "benchmark_bounds": [...],
  "interpretation": "...",
  "fragile": false
}
```

---

## Mode: hypotheses

Analysis of Competing Hypotheses (ACH). Based on Richards Heuer's CIA methodology, formalized with Bayesian LLR scoring. Use for entity investigation, anomaly evaluation, or any claim with multiple competing explanations.

See `references/evidence-matrix-template.md` for prediction table and report format. See `references/ach-scorer-example.md` for the Python API. See `references/ibe-dominance-format.md` for IBE criteria and dominance comparison.

For reasoning principles, read `references/reasoning-principles.md`.

### Phase 1: Constructive Abduction

1. **State the observation** in one sentence.
2. **Characterize observation geometry** -- shape-constrain hypotheses:
   - **Sharp break** -> at least one discrete event hypothesis
   - **Gradual erosion** -> at least one structural hypothesis
   - **Isolated cluster** -> at least one entity-specific hypothesis
   - **Sudden absence** -> at least one termination event hypothesis
   - **Oscillating** -> capital cycle, seasonal, or regulatory cycle
3. **Define the null generative process.**
4. **Check for lagged causes.**
5. **Identify the domain:** fraud detection, investment, regulatory, or mixed.
6. **Fetch base rates** if available.

**Output:**
> **Observation:** [quantified one-sentence pattern]
> **Geometry:** [sharp break / gradual / cluster / absence / cyclical]
> **Null process:** [baseline explanation]
> **Domain:** [fraud / investment / regulatory / mixed]
> **Base rate:** [from data or domain knowledge]

### Phase 2: Generate Hypotheses

Generate MINIMUM 3 competing hypotheses. Always include:
1. **The lead hypothesis** (what you suspect)
2. **Benign coincidence** (innocent explanation)
3. **Data artifact** (signal is noise, measurement error, methodology flaw)

For fraud: also Error, Regulatory arbitrage.
For investment: also Already priced in, Structural (new normal).

**Independence check (denial prompting):** After generating H1, state its core mechanism. Generate H2 under constraint: "Explain WITHOUT {H1's mechanism}." If you can't, note it as evidence H1 is strongly supported.

**Assign prior probabilities.** Must sum to 1.0.

### Phase 3: Predict Data Footprints (BEFORE querying)

For EACH hypothesis, predict what data footprint it would leave if true. Predictions BEFORE data prevent confirmation bias.

Write predictions in a table with P(evidence | hypothesis) in (0, 1). These are LIKELIHOODS, not posteriors. See `references/evidence-matrix-template.md`.

**Diagnosticity focus:** Prioritize predictions that DISTINGUISH hypotheses.

### Phase 4: Gather Evidence

Query data sources to test each prediction.
- Query ONE evidence item at a time
- Record what you find, not what you expected
- Zero rows IS evidence (absence can be diagnostic)
- Source-grade every finding: `[DATA]` for your analysis, Admiralty for external

### Phase 5: Score the Matrix

Score using Bayesian updating. See `references/ach-scorer-example.md`.

Interpret: posteriors, diagnosticity, inconsistency scores (most negative = REJECT), separation (log-odds gap: >1.0 = strong, <0.5 = inconclusive).

### Phase 5b: Inference to Best Explanation (IBE)

After Bayesian scoring, apply explanatory quality criteria. See `references/ibe-dominance-format.md` for 5 dimensions: scope, specificity, parsimony, unification, fertility.

**Fertility is the tiebreaker.** More NEW checkable predictions = more falsifiable = wins.

### Phase 5c: Falsification Queries

For each surviving hypothesis (posterior > 0.10):
1. Generate measurable implications ("If H is true, what SHOULD exist?")
2. Relevance check -- discard low-diagnosticity implications
3. Execute falsification searches. Record findings AND non-findings.
4. Update ACH matrix. Rescore.
5. Stop when one hypothesis dominates OR after 3 rounds without convergence.

### Phase 6: Kill or Promote

1. **Kill** hypotheses with posterior < 0.05 or bottom-quartile inconsistency. State WHY.
2. **Flag inconclusive** if separation < 0.5 between top two.
3. **Promote** if separation > 1.0 and posterior > 0.50.

### Phase 7: Write the Report

See `references/evidence-matrix-template.md` for report structure.

### Anti-Patterns

- **Shape mismatch.** Geometry constrains admissible hypotheses.
- **Confirmation over diagnosticity.** Focus on inconsistency, not confirmation.
- **Missing "data artifact" hypothesis.**
- **Correlated evidence inflating posteriors.** Collapse or use covariance-aware combination.
- **Ignoring absence.** Absence of expected evidence IS evidence against.
- **Prior sensitivity.** If verdict changes when you double/halve the leading prior, evidence is too weak.
- **Stopping at the matrix.** ACH directs investigation, not concludes it.
- **Forcing single-cause.** Multi-cause allowed with independent fingerprints.

---

## Mode: investigate

Deep forensic investigation methodology for datasets, entities, or systems. Adversarial, cross-domain, honest about provenance.

**NOT for:** academic literature review (use `/researcher`), software debugging, routine data analysis.

### Core Principles

1. **Adversarial stance:** Do NOT explain away anomalies. Quantify how wrong things look.
2. **Source grading:** Every claim graded on two axes (Admiralty system).
3. **Cross-domain triangulation:** 2+ independent confirmations from different domains: financial, enforcement, political, labor, corporate, market, journalism.
4. **Follow money to physical reality:** Does the entity exist? Who owns it? Where does money go?
5. **Name names:** Entities, people, dollar amounts, dates. Vague findings are useless.

### Pattern Recognition

Known fraud/abuse patterns:
- **Self-attestation:** Entity verifies its own work
- **PE playbook:** Acquire -> load debt -> extract -> bill at max -> flip
- **Regulatory capture:** Lobbyists write legislation, revolving door
- **Growth anomalies:** >100%/yr in industries where 5-15% is normal
- **Zombie entities:** Deactivated/excluded entities still billing

### Phase 1: Ground Truth Audit
Row counts, column types, date ranges, distributions. What CAN'T this data tell you?

### Phase 2: Structural Analysis
Concentration, variation, fastest growth, self-attestation patterns.

### Phase 3: Anomaly Hunting
Who bills the most? Who grew impossibly fast? Who charges 10x median? Who has 40%+ denial rates but keeps billing?

### Phase 4: Competing Hypotheses (ACH)
Apply ACH methodology (use `hypotheses` mode) for significant anomalies. Do not skip for leads above $10M.

### Phase 5: OSINT Layer
- **Officer/ownership spider:** Extract officers -> find all entities they control
- **Address clustering:** Find all entities at same address
- **Corporate DNA:** Where did sanctioned entity officers go next?
- **Fraud triangle signals:** Financial pressure on officers (lawsuits, liens, bankruptcy)

### Phase 6: External Validation
Journalism, government reports, enforcement actions, academic studies. Search for symptoms, not diagnoses.

### Phase 7: Cross-Domain Deep Dive
SEC filings, PE ownership chains, campaign finance, labor economics, physical verification, credit/bankruptcy.

### Phase 7b: Recitation Before Conclusion
Before writing synthesis, **restate the specific evidence** -- concrete data points, dollar amounts, dates, source grades. Then derive the conclusion. (Du et al., EMNLP 2025: +4% accuracy.)

### Phase 8: Synthesis
For each lead: ACH result, estimated exposure, EV score, network findings, recommended channel, key uncertainties.

### Memory-Efficient Data Analysis

For datasets >1GB, use DuckDB, not pandas:
```bash
uvx --with duckdb python3 << 'PYEOF'
import duckdb
con = duckdb.connect()
con.execute("COPY (SELECT ... FROM read_parquet('...')) TO '...' (HEADER, DELIMITER ',')")
con.close()
PYEOF
```

### Output (investigate mode)

- One "what is wrong" document (adversarial, no hedging)
- One "external confirmation" document (sourced validation)
- One "cross-domain" document (SEC, PE, political, labor)
- One "new leads" document (uninvestigated anomalies with ACH scores)
- CSV intermediates for reproducibility

---

## Linked Skills

- **`/researcher`** -- Use for external validation and literature search
- **`source-grading`** (auto-applied in investigate mode) -- Grade every claim on A1-F6 matrix

## Key References

- Pearl, J. -- *The Book of Why*, Ch. 4 (back-door criterion)
- Cinelli, C., Forney, A. & Pearl, J. (2022) -- "A Crash Course in Good and Bad Controls"
- Cinelli, C. & Hazlett, C. (2020) -- "Making Sense of Sensitivity" (JRSS-B)
- Elwert, F. & Winship, C. (2014) -- The bad-control problem
- Richards Heuer -- *Psychology of Intelligence Analysis* (ACH methodology)
- T3 benchmark -- LLMs default to CONDITIONAL 92% on ambiguous counterfactuals
- CauGym (Chen et al. 2026) -- Causal post-training, not available for general use
- Rung Collapse (arXiv:2602.11675) -- Autoregressive training cannot distinguish P(Y|X) from P(Y|do(X))

## Frontier Model Causal Reasoning Limits

LLMs retrieve causal associations, not reason causally. Don't trust the LLM to reason causally from prompts alone -- use deterministic scaffolding (DAGs, back-door criterion checks) to catch what the model cannot. See `references/reasoning-principles.md` section 15 for numbers.

$ARGUMENTS
