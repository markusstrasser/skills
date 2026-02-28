# Domain Profiles

Domain-specific gotchas for the researcher skill. These focus on non-obvious mistakes — evidence hierarchies are standard and don't need repeating. Classify the question's domain and apply the relevant profile.

If a question spans domains, name the primary and secondary. Use the stricter evidence standard. Project-specific tool routing (which databases, which views) lives in `.claude/rules/research-depth.md` if it exists.

## Scientific / Biomedical
- **Invoke `epistemics` skill** if available — it has the evidence hierarchy and grading rules.
- ClinVar single-submitter entries get reclassified often — don't treat as settled. ≥2 stars only.
- gnomAD frequency alone is not clinical evidence. PRS percentiles are population-relative, not absolute risk.
- You WILL fabricate supplement dosages and effect sizes under pressure to be precise. Don't.
- Rodent studies and mechanistic reasoning are hypothesis-generating, not evidence for human protocols.
- PubMed for clinical literature. Exa for recent work (Semantic Scholar can't filter by date on free tier).

## Trading / Investment
- **Invoke `source-grading` skill** if available — Admiralty grades, not provenance tags.
- **Detrend before claiming correlation.** Spurious correlations are the norm — control for market, seasonality, and shared trends before reporting any r value.
- Consensus = zero information. If every analyst says it, the price already reflects it.
- For high-conviction leads, use `/competing-hypotheses` to prevent single-hypothesis confirmation bias.
- **Predict the data footprint BEFORE querying.** Write what you expect to find, then query. Prevents confirmation bias.
- Check PIT (point-in-time) safety — disclosure lags vary by dataset (e.g., insider trades: 2-45 days, government spending: up to 365 days).
- Survivorship bias in backtests. Look-ahead bias in feature construction. Both invisible until you check.
- Absence of expected evidence IS evidence. If your hypothesis predicts X and X isn't there, that's diagnostic.

## Mathematics / Formal
- Reproduce derivations from source. Don't cite formulas from training data.
- You WILL invent coefficients, sample sizes, and p-values. The pattern: real concept + fabricated specifics.
- Verify probability vs odds vs log-odds at function boundaries — unit confusion is a real and common bug.
- Small-denominator metrics need Empirical Bayes shrinkage, not raw proportions.

## Investigative / OSINT
- **Invoke `source-grading` skill** if available — Admiralty grades mandatory.
- Grade claims, not datasets. The same dataset can have different reliability for different fields.
- **Predict the data footprint BEFORE querying.** If your hypothesis is true, what should you see in the data?
- Correlated signals (e.g., shared phone + shared address + shared official) can't be summed as independent log-likelihood ratios. Use composite scoring.
- Missing data ≠ no evidence. If actors hide information, missingness is evidence.
- The null hypothesis is always "error, not fraud." Don't skip it.

## Social Science
- Replication crisis is real. Check if the finding has been independently replicated before citing.
- WEIRD samples (Western, Educated, Industrialized, Rich, Democratic) — most psych findings are from US undergrads.
- Pre-registered studies > post-hoc analysis. Check if the study was pre-registered.

## Economics / Policy
- Ecological fallacy: aggregate patterns don't imply individual behavior.
- Policy effects are context-dependent. What worked in one country may not transfer.
- Goodhart's Law: when a metric becomes a target, it ceases to be a good metric.
