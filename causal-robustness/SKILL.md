---
name: causal-robustness
description: "Post-estimation sensitivity analysis. Quantifies how robust a causal estimate is to unmeasured confounding using PySensemakr (Cinelli-Hazlett OVB framework). Use AFTER fitting an OLS model."
effort: medium
---

# /causal-robustness

**When to use:** After specifying and fitting a regression model via `/causal-dag`.
**When NOT to use:** Before model fitting. For non-OLS models (logit, etc.) -- PySensemakr assumes linear models.

## Steps
1. Provide the fitted model formula + data path
2. `sensitivity_check.py` computes Robustness Value (RV)
3. Benchmarks against observed covariates
4. Interpretation: how strong would an omitted confounder need to be?

## Usage

```bash
uv run --with PySensemakr python3 sensitivity_check.py \
  --formula "Y ~ X + C1 + C2" \
  --data "path/to/data.csv" \
  --treatment "X" \
  --benchmark "C1,C2"
```

## Interpretation Guide

The Robustness Value (RV) represents the minimum strength of association (partial R-squared) an omitted confounder would need to have with BOTH treatment AND outcome to explain away the estimated effect.

Benchmarking uses `sensemakr.ovb_bounds()` which is 2D (partial R-squared with treatment AND outcome), not a scalar comparison.

- **RV > 2x strongest benchmark** -- robust. An omitted confounder would need to be more than twice as strong as the strongest observed covariate.
- **1x < RV < 2x** -- moderate. Note limitation in write-up.
- **RV < 1x** -- fragile. Revisit DAG for missing confounders before trusting the estimate.

## Output

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

## Relationship to Other Skills

- **`/causal-dag`** -- Use FIRST to specify the DAG and identify the valid adjustment set. Then fit the model, then run `/causal-robustness`.
- **`/causal-check`** -- Lightweight causal reasoning. `/causal-robustness` is for formal sensitivity analysis on fitted models.

## Key References

- Cinelli, C. & Hazlett, C. (2020) -- "Making Sense of Sensitivity: Extending Omitted Variable Bias" (JRSS-B)
- PySensemakr documentation: https://github.com/nlapier2/PySensemakr
