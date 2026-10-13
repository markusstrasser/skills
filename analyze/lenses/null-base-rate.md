# Null/Base-Rate Lens

Use before causal attribution.

1. State the observation with numbers and date range.
2. Define the null process: market/sector trend, seasonality, mean reversion,
   macro cycle, reporting cadence, or ordinary base rate. For a result from a
   stochastic agent or model run, the null is run-to-run spread: identical runs of
   one agent-model pairing varied more than different pairings did (arXiv:2609.33812),
   so one run per arm cannot separate them.
3. Remove the null if possible.
4. If the residual is small or within ordinary variance, stop with:
   `Null/base-rate explains the observation`.
5. If residual remains, classify its shape: sharp break, gradual erosion,
   isolated cluster, sudden absence, or cycle.

Output:

- Observation
- Null process
- Residual after null
- Residual geometry
- Whether further causal analysis is action-relevant
