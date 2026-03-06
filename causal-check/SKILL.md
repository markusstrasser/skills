---
name: causal-check
description: "Causal inference discipline for 'why' questions. Enforces explanatory specificity: match explanation shape to observation shape, define the null, predict new footprints, commit probabilistically. Prevents factor-listing and narrative-plausible-but-causally-wrong explanations."
---

# Causal Check

Invocation: `/causal-check OBSERVATION`

Where OBSERVATION is a "why did X happen" question, a root cause inquiry, or any causal claim to evaluate.

Triggers on: "why did", "what caused", "root cause", "explain the decline/rise/change in".

## When to Use

- Any "why" question about an observed pattern
- Root cause analysis for performance changes, anomalies, or trend breaks
- Before attributing causation to a correlation
- When you catch yourself listing plausible factors instead of identifying the specific cause

## When NOT to Use

- Pure prediction ("what will happen?") — use `/thesis-check`
- Competing explanations for entity-level fraud/error — use `/competing-hypotheses`
- Statistical anomaly screening — that's Phase 1, this is Phase 2

For full reasoning principles underlying this skill, read `references/reasoning-principles.md`.

## Phase 0: Characterize Observation

1. **State the observation** in one precise sentence with numbers. "Revenue declined" is not an observation. "Revenue declined 34% YoY in Q3 2025" is.

2. **Define the null generative process.** What baseline explains this observation without any special cause?
   - Market/sector trend (SPY up 20%, sector down 15%)
   - Random walk / mean reversion from prior extreme
   - Macro cycle (rate environment, GDP growth, seasonal)
   - Population/demographic base rate change

   If the null explains the observation, STOP. The answer is "nothing unusual happened." Detrending first (Brooklyn lesson: r=0.86 → 0.038).

3. **Characterize the residual geometry** (after removing the null):
   - **Sharp break** — abrupt level change at identifiable date
   - **Gradual erosion** — multi-year trend, no single inflection
   - **Isolated cluster** — affects specific entities/regions, not the class
   - **Sudden absence** — metric drops to zero or near-zero
   - **Oscillating/cyclical** — recurring pattern with period

4. **Check for lagged causes.** The cause may precede the effect by months/years. Regulatory changes (Reg FD: enacted Aug 2000, effective Oct 2000, impact visible 2001+). Capital cycles (investment decision → capacity online → margin compression: 2-5 year lag). Don't restrict search to coincident events.

5. **Quantify the magnitude.** What's the effect size? Is it within normal variance or 2+ sigma?

**Output format:**
> **Observation:** [precise, quantified]
> **Null:** [baseline explanation]
> **Residual after null:** [what remains unexplained]
> **Geometry:** [sharp break / gradual / cluster / absence / cyclical]
> **Magnitude:** [effect size, sigma from norm]
> **Lag window:** [how far back to search for causes]

## Phase 1: Generate Shape-Constrained Hypotheses

Generate 3-5 candidate explanations. Constrained by geometry:

| Geometry | MUST include | SHOULD include |
|----------|-------------|----------------|
| Sharp break | Discrete event (policy, leadership, product, enforcement) | Threshold/tipping point of gradual process |
| Gradual erosion | Structural shift (competition, demographics, technology) | Multiple compounding structural factors |
| Isolated cluster | Entity-specific cause (management, local regulation, fraud) | Selection/survivorship artifact |
| Sudden absence | Termination event (enforcement, bankruptcy, data change) | Measurement/reporting change |
| Oscillating | Cyclical driver (capital cycle, seasonal, regulatory) | Resonance between multiple cycles |

**Always include:**
- **"Data artifact / measurement change"** — the observation itself might be wrong
- At least one hypothesis that matches the observation geometry

**Multi-cause allowed** when each cause has independent, non-overlapping fingerprints. "Factor A drove the first 15% decline (evidenced by X), Factor B drove the remaining 20% (evidenced by Y)" is multi-cause. "Six things probably contributed" is factor-listing.

**Assign prior probabilities.** Use base rates from `memory/priors.md` where available. Must sum to 1.0.

## Phase 2: Seek Natural Experiment (if available)

Look for natural experiments that discriminate between hypotheses:

- **Cross-sectional variation:** Did the effect hit everyone, or only a subgroup? If Reg FD caused Buffett's decline, other information-edge investors should also decline post-2000.
- **Temporal variation:** Did the effect start at a specific date? Does it align with a hypothesis's predicted onset?
- **Geographic/regulatory variation:** Different jurisdictions with different rules → different outcomes?
- **Dose-response:** Entities more exposed to the hypothesized cause should show larger effects.

If no natural experiment exists, note this as an **epistemic limitation** — the causal claim is weaker without quasi-experimental evidence. This is information, not a blocker.

## Phase 3: Specificity Ranking

For each surviving hypothesis, evaluate:

1. **Temporal specificity:** Does the cause's timing match the effect's onset? (Sharp break at Oct 2000 → cause must be active Oct 2000 ± lag window)
2. **Magnitude specificity:** Does the cause's expected effect size match the observed magnitude?
3. **Scope specificity:** Does the cause predict the right affected population? (All fund managers vs. only information-edge investors)
4. **Mechanism specificity:** Can you trace the causal chain step-by-step? (Reg FD → eliminated selective disclosure → information edge lost → alpha disappeared)

**Anti-overfit test:** For the leading hypothesis, predict at least one NEW footprint you haven't checked yet.
- If Reg FD caused the decline, predict: other selective-disclosure-dependent investors also declined; Buffett's returns on new positions (not legacy holdings) should show the sharpest decline.
- Go check. If the new prediction fails, downgrade the hypothesis.

**Score each hypothesis:**
| Hypothesis | Temporal | Magnitude | Scope | Mechanism | New prediction | Total |
|-----------|----------|-----------|-------|-----------|---------------|-------|

## Phase 3b: Recursive Causal Audit (RCA)

Before committing, verify each surviving hypothesis step-by-step. This catches over-hedging (the dominant failure mode for frontier models — GPT-5.2 defaults to CONDITIONAL 92% of the time on ambiguous counterfactuals) and under-specified mechanism chains.

For the top 2 hypotheses, trace the causal chain:

**Step 1 — Mechanism chain:** Write each link in the causal chain explicitly.
```
H1: Reg FD → selective disclosure ended → information edge lost → alpha on new positions disappeared
     [policy]        [mechanism]              [intermediate]            [observable]
```

**Step 2 — Link-by-link audit:** For each link, ask:
- Is this link **directional** (A causes B, not just correlated)?
- Is this link **necessary** (without A, would B still happen)?
- Is this link **proportional** (does the size of A predict the size of B)?
- Could there be a **confounder** between A and B that you haven't named?
- Is any variable in this chain a **descendant** of the treatment? If so, you cannot condition on it without introducing collider bias.

**Step 3 — Identify the weakest link.** Which link has the least evidence? That's where to focus next.

**Step 4 — Check for bad controls.** If the analysis involves regression:
- List every control variable
- For each: is it pre-treatment, post-treatment, or a descendant of treatment?
- **Any descendant of treatment used as a control is a bad control** — flag immediately
- If this is a complex model, invoke `/causal-dag` for full DAG validation

**Output format:**
```
RCA for H1:
  Chain: A → B → C → D
  Link A→B: [directional: yes/no] [necessary: yes/no] [proportional: yes/no] [confounder risk: low/med/high]
  Link B→C: ...
  Weakest link: B→C (no direct evidence, inferred from timing)
  Bad controls: [none / list]
```

## Phase 4: Commit or Escalate

Based on specificity ranking:

**If one hypothesis dominates** (specificity score 2x+ the next):
> **Most likely cause (X%):** [hypothesis] — [one-sentence mechanism]
> **Top alternative (Y%):** [hypothesis] — [why it's less specific]
> **Falsifier:** [what evidence would disprove the leading hypothesis]
> **Decision impact:** [how this conclusion affects investment/investigation decisions]

**If two hypotheses are close** (within 1.5x specificity):
> **Inconclusive between:** [H1] and [H2]
> **Discriminating evidence needed:** [what data would separate them]
> **Provisional lean (X%):** [hypothesis] — [why, acknowledging uncertainty]

**If no hypothesis fits well:**
> **Honest answer:** The available evidence doesn't support a confident causal attribution.
> **Best available:** [hypothesis] at [low X%]
> **What would help:** [data/analysis needed]

"I don't know" is a valid and honest conclusion. Forced commitment with insufficient evidence is worse than acknowledged uncertainty.

## Output Requirements

Every `/causal-check` output MUST include:
1. **P(cause)** — probability assigned to the leading explanation
2. **Top alternative** — the second-best explanation and why it's less specific
3. **Falsifier** — what would disprove the leading explanation
4. **Decision impact** — what changes if the leading explanation is right vs. wrong

## Relationship to Other Skills

- `/causal-dag` — DAG construction + back-door validation for regression specs. Use when the causal check involves regression modeling. Phase 3b can escalate to full `/causal-dag` when the adjustment set is complex.
- `/competing-hypotheses` — full ACH matrix with Bayesian scoring. Use for entity-level investigation, leads >$10M. Heavier machinery, more evidence-gathering.
- `/causal-check` — lighter-weight causal discipline for "why" questions. Focuses on observation geometry and explanatory specificity. Can escalate to ACH if the question warrants it.
- `/thesis-check` — forward-looking investment stress test. Use after `/causal-check` establishes what happened and why.
