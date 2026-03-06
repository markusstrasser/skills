---
name: causal-dag
description: "DAG-first causal analysis. Forces directed acyclic graph construction and back-door criterion validation before any regression specification. Prevents bad-control, collider bias, and M-bias by making causal structure explicit."
---

# /causal-dag

**Invocation:** `/causal-dag VARIABLES` or `/causal-dag RESEARCH_QUESTION`

**Triggers:** "regression", "control for", "adjust for", "covariate", "confound", "causal effect of X on Y"

**When to use:**
- Before specifying ANY regression model
- Before adding covariates to an existing model
- When evaluating someone else's regression specification
- When the words "control for" appear

**When NOT to use:**
- Pure prediction (no causal claim) — use whatever predicts best
- Descriptive statistics
- Exploratory correlation

---

## Phase 1: Variable Classification

For every variable in the analysis, classify it. Do not skip this step. Do not classify by gut — state the temporal ordering and the causal mechanism for each.

| Variable | Classification | Temporal Order | Justification |
|----------|---------------|----------------|---------------|
| ... | Treatment (X) | ... | ... |
| ... | Outcome (Y) | ... | ... |
| ... | Pre-treatment confounder (C) | Before X | Causes both X and Y because... |
| ... | Mediator (M) | Between X and Y | On the causal path X -> M -> Y |
| ... | Descendant of treatment (D) | After X | Caused by X, do NOT control |
| ... | Descendant of outcome | After Y | Caused by Y |
| ... | Instrument (Z) | Before X | Causes X but not Y directly |
| ... | Collider | Varies | Caused by two+ variables — conditioning opens spurious path |

Classifications:
- **Treatment (X):** The exposure/cause of interest.
- **Outcome (Y):** What you're measuring the effect on.
- **Pre-treatment confounder (C):** Causes both X and Y. Temporally before X. These are the variables you SHOULD control for.
- **Mediator (M):** On the causal path X -> M -> Y. Do NOT control for unless you are explicitly decomposing direct vs indirect effects.
- **Descendant of treatment (D):** Caused by X. Do NOT control for total-effect estimation. Two failure modes: (1) **over-control** — blocks part of the causal path, attenuating the effect; (2) **collider bias** — if D also has other parents affecting Y, conditioning on D opens a spurious path. Many descendants trigger both.
- **Descendant of outcome:** Caused by Y. Do NOT control for.
- **Instrument (Z):** Causes X but has no direct effect on Y. Useful for IV estimation, not for OLS controls.
- **Collider:** Caused by two or more variables. Conditioning on it opens a spurious path between its parents.

---

## Phase 2: Draw the DAG

Represent the causal structure using text notation. Every arrow is a substantive claim about the world — treat it as such.

```
Sex -> Test_Score
Sex -> Items_Complete -> Test_Score   (Items_Complete is a DESCENDANT of treatment!)
Education -> Test_Score               (pre-treatment; Sex cannot cause Education for biological sex)
Room_Conditions -> Test_Score         (nuisance, not on causal path from X to Y)
```

Rules:
- Every arrow must have a direction and a justification
- If you're unsure about an edge, mark it with `[?]` and state what evidence would resolve it
- Temporal ordering constrains direction: causes precede effects. If A happens before B, the arrow cannot go B -> A.
- Do NOT add edges "just in case" — each edge is a claim. Unjustified edges create unjustified adjustment requirements.
- If there might be an unobserved common cause (U), draw it: `U -> X, U -> Y [unobserved]`

---

## Phase 3: Identify Adjustment Set

Using the DAG from Phase 2, identify the valid adjustment set for estimating the causal effect of X on Y.

**Back-door criterion:** Find a set of variables S such that:
1. No variable in S is a descendant of X
2. S blocks every back-door path from X to Y (paths with an arrow into X)

**Procedure:**
1. List all paths from X to Y
2. Mark which are causal (follow arrow direction from X to Y) — leave these OPEN
3. Mark which are back-door (have an arrow into X) — these must be BLOCKED
4. Find the minimal set S that blocks all back-door paths without opening collider paths

**Do NOT include in S:**
- Mediators — blocks the causal path, gives you the direct effect instead of the total effect
- Descendants of treatment — collider bias
- Descendants of outcome — biases the estimate
- Colliders on non-causal paths — conditioning opens the path (M-bias)

**Output:**
- **Valid adjustment set:** {C1, C2, ...}
- **Excluded and why:** M (mediator — blocks causal path), D (descendant of X — collider bias), ...
- **Remaining open back-door paths:** [any unblocked non-causal paths, or "none"]
- **Unobserved threats:** [any U variables that would invalidate the adjustment set if they exist]

---

## Phase 4: Bad-Control Audit

For EACH variable in the proposed (or planned) regression, audit against the DAG:

| Variable | In DAG? | Classification | In valid adjustment set? | Problem? |
|----------|---------|---------------|------------------------|----------|
| ... | Yes/No | ... | Yes/No | ... |

Flag anything that matches:

| Pattern | Flag | What goes wrong |
|---------|------|-----------------|
| Descendant of X used as control | **OVER-CONTROL / COLLIDER BIAS** | Over-control: blocks part of the causal effect (attenuates estimate). Collider bias: if the descendant has other parents affecting Y, conditioning opens a spurious path. Can reverse the sign of the true effect. |
| Mediator used as control | **OVER-CONTROL** | Blocks the causal path X -> M -> Y. You get the direct effect minus the mediated effect, not the total causal effect. |
| Variable not in DAG | **UNJUSTIFIED** | What is the causal story? If you can't place it in the DAG, you can't justify including it. |
| Collider being conditioned on | **SPURIOUS PATH OPENED** | Conditioning on a collider opens a non-causal path between its parents. |
| Post-treatment variable | **POST-TREATMENT BIAS** | Even if not a descendant of X, post-treatment variables can be affected by X through unmeasured paths. |

If any flag fires, STOP. Do not proceed to Phase 5. Fix the specification first.

---

## Phase 5: Specification Output

Only after Phases 1-4 pass clean.

```
Model:      Y ~ X + C1 + C2
Treatment:  X
Controls:   C1 (pre-treatment confounder: causes both X and Y via ...),
            C2 (pre-treatment confounder: causes both X and Y via ...)
Excluded:   M (mediator — on causal path X -> M -> Y),
            D (descendant of X — collider bias)
Estimand:   Average causal effect of X on Y, conditional on {C1, C2}
Assumptions:
  1. No unmeasured confounding given {C1, C2}
  2. DAG is correctly specified (edges and directions)
  3. [any functional form assumptions — linearity, additivity]
Threats:    [what unmeasured variables could invalidate this]
```

---

## Output Requirements

Every `/causal-dag` invocation MUST produce all of these:

1. Variable classification table (Phase 1)
2. DAG in text notation (Phase 2)
3. Valid adjustment set with exclusions and reasons (Phase 3)
4. Bad-control audit table (Phase 4)
5. Clean regression specification (Phase 5) — or a STOP with what needs fixing
6. Remaining assumptions and threats — what could still be wrong

Do not skip phases. Do not compress phases into prose. The tables are the point.

---

## Worked Example: The Bad-Control Trap

Research question: "What is the causal effect of sex on cognitive test scores?"

A naive agent might specify: `Test_Score ~ Sex + Education + Items_Complete + Room_ID`

**Phase 1 catches it:**

| Variable | Classification | Temporal Order | Justification |
|----------|---------------|----------------|---------------|
| Sex | Treatment (X) | Fixed at birth | Exposure of interest |
| Test_Score | Outcome (Y) | At test time | What we're measuring |
| Education | Pre-treatment confounder (C) | Before test | Affects both opportunity and score |
| Items_Complete | Descendant of treatment (D) | During test | Sex -> engagement -> items completed |
| Room_ID | Nuisance | At test time | Affects score, not caused by sex |

**Phase 4 catches it:**

| Variable | In DAG? | Classification | In adjustment set? | Problem? |
|----------|---------|---------------|-------------------|----------|
| Sex | Yes | Treatment | N/A | - |
| Education | Yes | Confounder | Yes | OK |
| Items_Complete | Yes | Descendant of X | NO | **COLLIDER BIAS** |
| Room_ID | Yes | Nuisance | Yes | OK (not on causal path, not a descendant) |

**STOP.** Remove `Items_Complete`. It is caused by Sex (via engagement, stamina, strategy differences). Conditioning on it opens a spurious path: `Sex -> Items_Complete <- Other_Causes_of_Completion -> Test_Score`.

**Correct specification:** `Test_Score ~ Sex + Education + Room_ID`

---

## Common Traps

1. **"Just control for everything available."** No. Each control variable is a causal claim. Adding a descendant of treatment as a control can reverse or attenuate the true effect. More controls != less bias.

2. **"More controls = less bias."** False for descendants and colliders. The bias from a bad control can exceed the bias from omitting a confounder.

3. **"The reviewer/supervisor asked us to control for X."** Check the DAG first. Reviewers can be wrong. If X is a descendant of treatment, controlling for it is wrong regardless of who requested it.

4. **"It's a covariate, not a control."** Semantics. If it's in the conditioning set of the regression, it's a control. It adjusts the estimate. The DAG doesn't care what you call it.

5. **"We're just being conservative."** Including a collider is not conservative — it introduces bias that wasn't there before. Conservative means fewer assumptions, not more variables.

6. **"The coefficient on X changed when we added Z, so Z must be a confounder."** Not necessarily. If Z is a collider or descendant, the change reflects bias being introduced, not removed.

---

## Relationship to Other Skills

- **`/causal-check`** — Lightweight "why did X happen" analysis for observations. Use `/causal-dag` when you need to SPECIFY a regression model. Use `/causal-check` when you need to EXPLAIN an observed outcome.
- **`/competing-hypotheses`** — Structured hypothesis comparison. Use AFTER `/causal-dag` has established the causal structure. The DAG tells you which hypotheses are testable and what the confounding structure looks like.
- **`/researcher`** — May invoke `/causal-dag` when the research involves regression or causal analysis. The researcher skill should not specify regressions without running this first.

---

## Key References

- Pearl, J. — *The Book of Why*, Ch. 4 (back-door criterion)
- Cinelli, C., Forney, A. & Pearl, J. (2022) — "A Crash Course in Good and Bad Controls"
- Elwert, F. & Winship, C. (2014) — The bad-control problem: conditioning on a descendant of treatment creates collider bias
- T3 benchmark — LLMs default to CONDITIONAL interpretation 92% of the time on ambiguous counterfactuals. They need structural scaffolding to get causal reasoning right.
- CauGym (Chen et al. 2026) — Causal post-training helps but is not available for general use yet. This skill is the manual substitute.
