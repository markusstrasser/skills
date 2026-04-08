# Domain Profiles

Domain-specific gotchas for the researcher skill. These focus on non-obvious mistakes — evidence hierarchies are standard and don't need repeating. Classify the question's domain and apply the relevant profile.

If a question spans domains, name the primary and secondary. Use the stricter evidence standard. Project-specific tool routing (which databases, which views) lives in `.claude/rules/research-depth.md` if it exists.

## Exa Category Routing

When using `web_search_advanced_exa`, set `category` to narrow results:

| Domain | Category | When |
|--------|----------|------|
| Finance/investing | `financial report` | SEC filings, earnings, annual reports |
| Academic research | `research paper` | Supplements S2, better recency than S2 free tier |
| Current events | `news` | Press releases, regulatory announcements |
| Company analysis | `company` | Company profiles, products, overview |
| Code/technical | `github` | Repos, issues, discussions |

Omit `category` when the query spans domains or when you want diverse source types.

## Scientific / Biomedical
- **Invoke `epistemics` skill** if available — it has the evidence hierarchy and grading rules.
- **For precise numbers** (gene coordinates, protein sizes, odds ratios, allele counts): use `perplexity_ask` first. Empirical benchmark (8 genomics questions, Mar 2026): Perplexity returned exact values with CIs and assembly versions; Exa `/answer` confirmed/denied but omitted precision (couldn't extract BRCA1 amino acid count, gave "~3.1B" instead of 3,298,912,062 for GRCh38). Use `verify_claim` only when you already have the number and need a yes/no check.
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

## Adversarial Mode — Domain-Specific Query Patterns

When running `--adversarial`, tailor Exa queries to the domain. Generic "X criticism" finds opinion pieces; domain-shaped queries find the real evidence.

### Biomedical / Clinical
- "sham surgery RCT [intervention] no better than placebo"
- "[intervention] Cochrane review no effect"
- "[drug/gene] candidate gene failed to replicate GWAS"
- "medical reversal [intervention] Vinay Prasad"
- "overdiagnosis [condition] screening NNT"
- Check: Ioannidis-style "most findings are false" priors apply maximally here (small samples, flexible designs, financial incentives)

### Genomics / Genetics
- "[gene] Border et al candidate gene replication failure"
- "PRS [trait] within-family analysis confounding"
- "GWAS [trait] omnigenic Boyle"
- "[variant] ClinVar reclassification VUS"
- Check: candidate gene vs GWAS-replicated distinction is the first filter. If a gene/variant has no GWAS Catalog entry, it's a candidate gene descendant until proven otherwise.

### AI / ML
- "[benchmark] saturated contaminated gaming Goodhart"
- "[method] failed to reproduce independent evaluation"
- "[capability claim] actually measures [simpler thing]"
- "LLM [task] capability reliability gap"
- Check: Demo ≠ benchmark ≠ deployment. Most impressive demos don't survive systematic evaluation.

### Psychology / Social Science
- "[effect] failed replication pre-registered"
- "[effect] statistical artifact regression to mean"
- "[study] WEIRD sample generalization failure"
- "[effect] Kahneman retraction acknowledgment"
- Check: easy target but important — many debunked findings are still taught and cited. The candidate-gene-era equivalent: priming, ego depletion, power posing, growth mindset (as intervention).

### Nutrition / Epidemiology
- "[dietary claim] randomized controlled trial contradicts observational"
- "[food] healthy user bias confound"
- "[nutrient] Ioannidis vibration of effects"
- Check: relative risk <2.0 from observational studies is noise until proven otherwise (Ioannidis's rule of thumb). Confounding by "healthy user" behavior explains most dietary associations.

### Engineering / Technology
- "[technology] real-world failure rate vs lab performance"
- "[system] worked in demo failed in production"
- "[material/method] theoretical limit vs achieved performance gap"
- Check: Lab conditions ≠ field conditions. Scaling laws break. Integration failures dominate.

### Economics
- "[result] coding error replication failure"
- "[theory] natural experiment invalid instrument"
- "[policy] reversed when [country] actually tried it"
- Check: Reinhart-Rogoff pattern — coding errors, data selection, and instrument validity are the three kill shots.

### Humanities / Critical Theory
- "[theory] unfalsifiable no predictive power"
- "[framework] replication conceptual crisis"
- "[field] Sokal affair grievance studies hoax"
- Check: Different failure mode — not false precision but unfalsifiability. The critique here is structural: does the framework make predictions that could be wrong? If not, it's theology, not scholarship.
