# Analytical Reasoning Principles (Cross-Project)

Core reasoning discipline for investigation, analysis, and causal inference. Every principle survived multi-model review (GPT-5.2 + Gemini 3.1 Pro, 2026-02-27). Source-graded per NATO Admiralty system.

**Provenance:** Commoncog (Cedric Chin) frameworks → Claude Opus synthesis → GPT-5.2 formal verification → Gemini 3.1 Pro adversarial review

Referenced by: `/causal-check`, `/competing-hypotheses`, `/investigate`

---

## 1. Environment Regularity Gate

Before trusting any pattern-matching intuition (Klein RPD), classify the task environment. `[B1]` Klein/Kahneman joint work + GPT-5.2 formalization.

**Three tiers** (not binary — GPT-5.2 corrected the original binary framing):

| Tier | Definition | Trust intuition? |
|------|-----------|-----------------|
| **Regular** | Stationary cue→outcome mapping, fast unbiased feedback, low adversarial shift | Yes — RPD valid |
| **Semi-regular** | Patterns recur but labels are biased, adversarial adaptation is slow | Partially — use as lead generator, verify with structured analysis |
| **Irregular** | Sparse/delayed feedback, strong nonstationarity, severe label selection bias | No — default to rational frameworks (ACH, backtest) |

**Formal requirements for regularity** (GPT-5.2):
1. Approximate stationarity: P_t(Y|X) ≈ P_{t+Δ}(Y|X)
2. Sufficiently fast + unbiased feedback
3. Low adversarial covariate shift (measuring doesn't change the process)

**When regularity breaks:**
- Regime changes (policy, rate resets)
- Adversarial adaptation (Goodhart: actors suppress screened cues)
- Outcome feedback delayed >2 years or sparse (<10 cases)
- Label bias dominates (learning "what gets caught")

---

## 2. Phase 1/2 Bifurcation (Renaissance vs. Klein)

Resolves the conflict between narrative-free statistical screening and hypothesis-driven investigation. `[C2]` Gemini 3.1 synthesis.

| Phase | Mode | Method | When |
|-------|------|--------|------|
| **Phase 1: Screening** | Renaissance (no narrative) | Pure statistical anomaly detection. No hypotheses, no stories. | Automated alerts, batch processing |
| **Phase 2: Investigation** | Klein (mental simulation) | Form hypothesis, predict expected data footprint, query, compare prediction to reality. | After flagging, before deep analysis |

**Phase 2 protocol:**
1. State hypothesis: "If X is happening..."
2. Predict expected footprint: "...I expect to see Y in data source A, Z in source B"
3. Query the data
4. Compare prediction to reality
5. Mismatches are more informative than confirmations

**Do NOT mix phases.** Running Phase 1 with a narrative biases the screen. Running Phase 2 without a prediction wastes diagnostic power.

---

## 3. Quantify Before Narrating

The first response to any anomaly should be a number, not a story. `[DATA]`

- Compute the base rate before interpreting the anomaly
- Scope risk to affected revenue (not total enterprise value)
- If the narrative sounds compelling before the math checks out, treat it as a WARNING
- Consensus-matching conclusions add zero information (Heuer: evidence consistent with all hypotheses has zero diagnostic value)

---

## 4. Anti-Goodhart Discipline

"When a measure becomes a target, it ceases to be a good measure." The fix is to test for gaming signatures. `[B2]` Commoncog/Wheeler + GPT-5.2.

**Four testable gaming signatures:**
1. **Bunching near thresholds** — density spike just below known limits
2. **Suppressed variance** — unnaturally low CoV vs. cohort
3. **Structural breaks around rule changes** — difference-in-differences around implementation dates
4. **Substitution effects** — monitored metric improves while activity shifts to unmonitored margin

**For your own metrics:** Separate measurement from incentive. Who benefits from this number being high? Are they reporting it?

---

## 5. Evidence Correlation Discipline

Summing independent-evidence scores (LLRs, Z-scores) assumes conditional independence. Correlated signals inflate posteriors. `[B1]` GPT-5.2 formal proof.

**Fix A:** Collapse correlated signals into one composite feature.
**Fix B:** Covariance-aware combination: Z_comb = Σ(w_i × Z_i) / √(w^T Σ w)

**Rule:** For ranking (ordinal), summed scores are acceptable. For confidence estimates (cardinal), use composite features or covariance-aware combination.

---

## 6. Sample from Opposed Incentive Structures

Before trusting any single-source claim, identify who benefits from this information being believed. `[B2]` Intelligence tradecraft.

If your conclusion matches the incentive of your primary information source, you haven't learned anything — you've been recruited. Seek the adversarial view before committing.

---

## 7. Domain Labeling

Explicitly mark when switching inference modes. Each domain has different evidence standards and failure modes. `[DATA]`

| Domain | Evidence standard | Common failure |
|--------|------------------|----------------|
| Statistical detection | p-values, effect sizes, base rates | Multiple comparisons, confounders, overfitting |
| Sociological explanation | Institutional analysis, trust networks | Just-so stories, ecological fallacy |
| Legal evidence | Beyond reasonable doubt, admissibility | Relevance ≠ admissibility, privilege |
| Political analysis | Incentive mapping, power dynamics | Unfalsifiable narrative, conspiracy thinking |
| Financial analysis | DCF, multiples, cash flow | P/E hallucination, survivorship bias |

---

## 14. Explanatory Specificity (Causal Inference Discipline)

The quality of an explanation is measured by its specificity to the observed pattern, not by its plausibility in general. `[DATA]` — lesson from Buffett analysis (2026-03-03). Cross-model reviewed.

**The failure mode:** Autoregressive models default to P(Y|X) not P(Y|do(X)) (Chang et al., arXiv:2602.11675). This produces factor-listing: six gradual causes for a sharp break.

**The discipline:**
1. **Characterize observation geometry first.** Sharp break? Gradual erosion? Isolated cluster? Sudden absence?
2. **Shape-constrain hypothesis generation.** Sharp breaks demand discrete-event candidates. Gradual trends demand structural candidates.
3. **Define the null generative process.** What baseline explains this without any special cause?
4. **Multi-cause allowed when each cause has independent, non-overlapping fingerprints.**
5. **Validate specificity by predicting NEW footprints.** Anti-overfit: does your explanation predict something you haven't checked yet?
6. **Commit probabilistically.** "Most likely at X%" with a named falsifier. "I don't know" is valid.

**Shape→cause mappings are probabilistic heuristics, not logical derivations.** A sharp break makes a discrete event more likely (~70%), not certain.

---

## 15. Frontier Model Causal Reasoning Limits (2026 Evidence)

LLMs retrieve causal associations, not reason causally. Key numbers from T3 benchmark (Chang, Stanford, arXiv:2601.08258):

| Model | L1 Association | L3 Counterfactual | Primary failure |
|-------|---------------|-------------------|-----------------|
| GPT-4-Turbo | 100% | 71.5% | Over-hedge 12% |
| GPT-5.2 | 95% | 59.5% | Over-hedge 15%, Fatalism 10% |
| Claude Sonnet 4.5 | 80% | 56.0% | Fatalism 14% |

**Scaling Paradox:** Bigger models are WORSE at counterfactuals (GPT-5.2 < GPT-4-Turbo). RLHF safety training suppresses causal judgment — the model defaults to "CONDITIONAL" 92% of the time.

**Rung Collapse (arXiv:2602.11675):** Formally proven that autoregressive training provides no gradient signal to distinguish P(Y|X) from P(Y|do(X)). LLMs operate at Pearl's Rung 1 and dress it as Rung 2.

**Implication for skills:** Don't trust the LLM to reason causally from prompts alone. Use deterministic scaffolding (DAGs, back-door criterion checks, `dag_check.py`) to catch what the model cannot.

**Counter-evidence:** CauGym (arXiv:2602.06337, 2026) shows causal post-training on a 14B model hits 93.5% on CaLM vs 55.4% for o3. But this requires specialized training, not available in general-purpose models.

---

## Meta-Principle: Error Correction IS the Product

Corrections (detrending lessons, hallucination catches, resolution fixes) ARE the tacit knowledge that compounds. Track epistemic evolution. Retractions, upgrades, and downgrades are the artifacts that compound intelligence.
