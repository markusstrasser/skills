---
name: epistemics
description: Bio/medical/scientific evidence hierarchy and anti-hallucination rules. Use when conducting claim-heavy medical research, genomics interpretation, supplement evaluation, pharmacogenomics, or clinical evidence synthesis. NOT for casual health questions, software engineering, or physics. Companion to deep-research skill.
user-invocable: false
---

# Bio/Medical Research Epistemics

Domain-specific guardrails for scientific research. Use alongside `deep-research` for the workflow; this skill provides the evidence hierarchy, anti-hallucination rules, and bio-specific failure modes.

## Anti-Hallucination Rules (non-negotiable)

1. **Citation requirement:** Every non-trivial factual claim needs a resolvable citation (DOI, PMID, ClinicalTrials.gov ID, or official URL). If you can't cite it, label "UNCITED."

2. **No fake citations:** Never invent paper titles, authors, journals, or numbers. If you can't find the paper, say so.

3. **Separate evidence layers:** Keep strictly distinct:
   - (a) In vitro / cell culture
   - (b) Animal model (species, dose, route)
   - (c) Human observational / GWAS association
   - (d) Human RCT — surrogate endpoint (biomarker)
   - (e) Human RCT — clinical outcome (patient-important)
   - (f) Systematic review / meta-analysis
   - (g) Clinical guideline / consensus statement

   NEVER let (a-c) substitute for (d-g). Say explicitly: "Mechanistic evidence only; no human clinical trial confirms this."

4. **Quantify uncertainty:** Effect sizes need CIs or ranges. State population, comparator, timeframe. For genetic associations: OR + CI + population + MAF.

5. **Genetic claims:** Distinguish GWAS association vs functional validation vs clinical actionability. State penetrance. "Associated with" ≠ "causes." Single-SNP interpretation of polygenic traits is usually misleading. PGx claims need CPIC/DPWG level.

6. **Dosing guardrails:** Rx = guideline ranges only ("discuss with prescriber"). OTC/supplements = evidence-based ranges if cited. Genotype→dose only with CPIC/DPWG-level evidence, otherwise label INFERENCE.

## Evidence Hierarchy

Grade every claim:

| Grade | Type | Notes |
|-------|------|-------|
| 1 | Clinical guideline / consensus | NICE, WHO, AAD, CPIC, DPWG |
| 2 | Systematic review / meta-analysis | Cochrane, PRISMA-compliant |
| 3 | Well-powered RCT | Pre-registered, independent, adequate N |
| 4 | Small / pilot RCT | Underpowered, often industry-funded |
| 5 | Large observational / cohort | Adjusted, replicated |
| 6 | GWAS / genetic association | Report OR, CI, population, replication |
| 7 | Animal model | Species, dose, route — note translatability |
| 8 | In vitro / cell culture | Note concentration vs physiological |
| 9 | Case report / expert opinion | Lowest weight |

Always note: COI, replication status, sample size, population match, effect size (NNT, ARR, or Cohen's d when available).

## Inference Rules

You may reason from first principles, but MUST label it INFERENCE.

Any INFERENCE must include:
- Assumptions stated explicitly
- A minimal derivation (with units)
- Sensitivity: what if the key assumption is 2x off?

Three buckets in every output:
1. **EVIDENCE** — cited, graded
2. **INFERENCE** — derived from evidence + assumptions, labeled
3. **PRACTICAL** — availability, cost, formulation; never upgraded to efficacy claims

## Bio-Specific Failure Modes

Check yourself against each before outputting:

- **Genotype→phenotype leap:** Treating GWAS association (OR 1.1-1.5) as deterministic prediction. Fix: state OR, CI, population, penetrance.
- **Concentration confusion:** Citing in vitro effect at 100μM as evidence for 500mg oral supplement without bioavailability discussion. Fix: check if effective concentration is physiologically achievable.
- **Supplement industry bias:** Most supplement RCTs are small, industry-funded, surrogate endpoints, positive publication bias. Fix: flag funding, N, endpoint type.
- **Protocol broadcasting:** Treating Huberman/Attia/Sinclair recommendation as evidence. Fix: trace to primary study and grade independently.
- **N=1 extrapolation:** "Bryan Johnson does X" = anecdote, not evidence.
- **False binary:** "This SNP means you can't convert X" when actual effect is 20-40% reduction. Fix: quantified ranges, not categorical language.
- **Directionality error:** Citing real study but inverting the sign. Fix: explicitly state what changes, which moiety, direction for each step.
- **Inference promotion:** Plausible mechanistic chain presented as decision-grade evidence. Fix: put in explicit INFERENCE section with assumptions + failure modes.
- **Genotype-only search:** Only searched genotype→supplement, never condition→supplement. Fix: ALWAYS run condition-anchored search axis in parallel.

## LLM-Specific Failure Modes

| Model | Failure Mode | Severity |
|-------|-------------|----------|
| Claude | Sycophantic hedging; agrees then qualifies until useless | Medium |
| Claude | Citation-shaped bullshit; plausible references that don't exist | High |
| Claude | Genotype determinism; treats associations as deterministic | High |
| GPT | Confident fabrication; invents complete fake studies with authors and N | Critical |
| GPT | Overcitation; cites 20+ papers, many tangential or unverifiable | Medium |
| Gemini | Google-source bias; over-relies on Scholar snippets without reading papers | High |
| Gemini | Length inflation; massive outputs that bury the signal | Medium |

## Self-Audit Checklist

After any bio research output:
- [ ] Every number has a source (DOI/PMID/URL)
- [ ] No study cited that you haven't verified exists
- [ ] In vitro/animal evidence NOT used to justify clinical recommendations
- [ ] Genetic associations include OR, CI, population, penetrance
- [ ] "Cannot/always/never" replaced with quantified ranges
- [ ] Industry-funded studies flagged
- [ ] Supplement doses cite the study they come from
- [ ] Genotype→dosing claims have CPIC/DPWG level or labeled INFERENCE
- [ ] Confidence ratings are honest
- [ ] Counterarguments section exists and is substantive

## PGx Quick Reference

**Justified:** CPIC Level A/B, PharmGKB Level 1A/1B.
**Not justified (but LLMs do it):** Single GWAS hit OR<2.0→dose recommendation; nutrigenomic SNP→supplement dose; variant without replication in user's ancestry.

**Key databases:** CPIC (cpicpgx.org), PharmGKB, ClinVar, DPWG, gnomAD.

## Non-Paper Evidence (acceptable, labeled)

- Regulatory: FDA/EMA monographs, drug labels, safety communications
- Grey literature: ClinicalTrials.gov entries, conference posters, preprints [PREPRINT]
- Independent testing: ConsumerLab, Labdoor, third-party CoAs
- PGx databases: PharmGKB, ClinVar, CPIC guidelines
- Operational: formulation stability, supply chain, product CoAs
