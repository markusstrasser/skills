<!-- Reference file for competing-hypotheses skill. Loaded on demand. -->

# ACH Scorer Usage

## Python API (ach_scorer.py)

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

## Manual Computation

If no scorer is available, compute manually:

```
posterior ∝ prior × Π(likelihoods)
```

Normalize so posteriors sum to 1.0.

## Interpreting Output

- **Posteriors**: updated probabilities after evidence
- **Diagnosticity**: which evidence most differentiates hypotheses (focus investigation here)
- **Inconsistency scores**: Heuer's method -- most negative = most inconsistent = REJECT
- **Separation**: log-odds gap between top two hypotheses. >1.0 = strong, <0.5 = inconclusive
