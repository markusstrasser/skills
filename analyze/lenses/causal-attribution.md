# Causal Attribution Lens

Use for "why did X happen?" after the null/base-rate lens leaves a meaningful
residual.

1. List the observations the answer must explain, as bare facts separate from
   anyone's proposed explanation.
2. Generate 3-5 shape-constrained hypotheses, including data artifact or
   measurement change, a competing mechanism to the favored one, and `H_other`
   (a cause not listed). Drop any that fails to explain a listed observation.
3. Assign priors that sum to 1.0, with `H_other` small but non-zero.
4. Look for natural experiments: timing, subgroup, geography, dose-response.
5. Rank by temporal, magnitude, scope, and mechanism specificity. If the leader
   leaves a listed observation unexplained, generate again before ranking.
6. Check one new footprint predicted by the leading hypothesis.

Output:

- P(cause) for the leading explanation
- top alternative and why it is weaker
- falsifier
- decision impact
