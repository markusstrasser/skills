---
name: causal-dag
description: "DAG-first causal analysis. Forces directed acyclic graph construction and back-door criterion validation before any regression specification. Prevents bad-control, collider bias, and M-bias by making causal structure explicit."
effort: high
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

For every variable, classify it. State the temporal ordering and causal mechanism for each.

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

**Verification Gate 1:** (1) Every variable classified into exactly one role. (2) Plausible alternative classifications listed with resolving evidence. (3) Each confounder causes BOTH treatment and outcome — state mechanism for each direction.

---

## Phase 2: Construct the DAG (4-stage decomposition)

Build in four stages: skeleton, V-structures, Meek rules, flag undirected. See `references/dag-construction.md` for detailed procedure and Meek rules.

**Gate:** Temporal defensibility of every edge. Missing edges are claims of no relationship. All colliders intentional. No cycles. V-structures valid after propagation.

---

## Phase 3: Identify Adjustment Set

Find set S satisfying the back-door criterion. See `references/adjustment-algorithms.md` for procedure.

**Do NOT include:** mediators, descendants of treatment, descendants of outcome, colliders on non-causal paths.

---

## Phase 4: Bad-Control Audit

For EACH variable in the proposed regression, audit against the DAG:

| Variable | In DAG? | Classification | In valid adjustment set? | Problem? |

**Trap catalog — if any fires, STOP:**

| Pattern | Flag | What goes wrong |
|---------|------|-----------------|
| Descendant of X used as control | **OVER-CONTROL / COLLIDER BIAS** | Blocks causal effect (attenuates) or opens spurious path if descendant has other parents affecting Y. Can reverse the sign. |
| Mediator used as control | **OVER-CONTROL** | Blocks X -> M -> Y. You get direct minus mediated, not total effect. |
| Variable not in DAG | **UNJUSTIFIED** | No causal story = no justification for inclusion. |
| Collider being conditioned on | **SPURIOUS PATH OPENED** | Opens non-causal path between its parents. |
| Post-treatment variable | **POST-TREATMENT BIAS** | Even if not a descendant of X, can be affected through unmeasured paths. |

If any flag fires, fix the specification before proceeding.

---

## Phase 5: Specification Output

Only after Phases 1-4 pass clean. See `references/output-templates.md` for template and consensus mode.

---

## Output Requirements

Every `/causal-dag` invocation MUST produce all of these:

1. Variable classification table (Phase 1)
2. DAG in text notation (Phase 2)
3. Valid adjustment set with exclusions and reasons (Phase 3)
4. Bad-control audit table (Phase 4)
5. Clean regression specification (Phase 5) — or a STOP with what needs fixing
6. Remaining assumptions and threats

Do not skip phases. Do not compress phases into prose. The tables are the point.

---

## Common Traps

1. **"Just control for everything available."** Each control is a causal claim. Adding a descendant of treatment can reverse or attenuate the true effect.

2. **"More controls = less bias."** False for descendants and colliders. Bad-control bias can exceed omitted-confounder bias.

3. **"The reviewer asked us to control for X."** Check the DAG. Reviewers can be wrong. If X is a descendant of treatment, controlling for it is wrong regardless of who requested it.

4. **"It's a covariate, not a control."** If it's in the conditioning set, it adjusts the estimate. The DAG doesn't care what you call it.

5. **"We're just being conservative."** Including a collider is not conservative — it introduces bias that wasn't there before.

6. **"The coefficient changed when we added Z, so Z must be a confounder."** If Z is a collider or descendant, the change reflects bias being introduced, not removed.

---

## References

- `references/dag-construction.md` — 4-stage DAG decomposition, Meek rules, edge format for dag_check.py
- `references/adjustment-algorithms.md` — Back-door criterion procedure, exclusion rules
- `references/output-templates.md` — Specification template, consensus mode (--consensus)
- `references/worked-example.md` — Bad-control trap worked example (sex -> test scores)

---

## Relationship to Other Skills

- **`/causal-check`** — Lightweight "why did X happen" for observations. Use `/causal-dag` to SPECIFY a regression model.
- **`/causal-robustness`** — Post-estimation sensitivity analysis (PySensemakr). Use AFTER fitting an OLS model specified via `/causal-dag`.
- **`/competing-hypotheses`** — Structured hypothesis comparison. Use AFTER `/causal-dag` has established causal structure.
- **`/researcher`** — May invoke `/causal-dag` when research involves regression or causal analysis.

---

## Key References

- Pearl, J. — *The Book of Why*, Ch. 4 (back-door criterion)
- Cinelli, C., Forney, A. & Pearl, J. (2022) — "A Crash Course in Good and Bad Controls"
- Elwert, F. & Winship, C. (2014) — The bad-control problem
- T3 benchmark — LLMs default to CONDITIONAL interpretation 92% of the time on ambiguous counterfactuals
- CauGym (Chen et al. 2026) — Causal post-training helps but is not available for general use yet
