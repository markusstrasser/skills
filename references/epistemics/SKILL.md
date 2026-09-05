---
name: epistemics
description: Bio/medical/scientific evidence and anti-hallucination reference for claim-heavy medical research, genomics interpretation, supplement evaluation, pharmacogenomics, or clinical synthesis. Not a workflow for casual health questions or other technical domains.
user-invocable: false
effort: high
---

# Bio/medical research epistemics

Use with [research](../../research/SKILL.md). Apply checks to the claims the task actually makes; an evidence review does not require a dosing, purchasing or implementation plan.

## Source and claim integrity

- Support consequential factual claims with a resolvable DOI, PMID, registry record or official URL. Verify source identity and the relevant contents. Mark unsupported claims as unresolved; never invent study details or references.
- Separate cell culture, animal work, human observational/genetic associations, randomized trials, systematic reviews and clinical recommendations. Distinguish surrogate endpoints from patient-important outcomes. Mechanistic or animal evidence alone cannot establish human clinical efficacy.
- For an effect estimate, report population, comparator, outcome, timeframe, magnitude and uncertainty when available. Mark missing quantities rather than fabricating them. Distinguish relative from absolute effects and check directionality.
- For genetic claims, distinguish association, functional validation and clinical actionability. State relevant ancestry, allele/build and uncertainty; use OR/CI, allele frequency or penetrance where the claim requires and the source supplies them. A polygenic trait is not determined by one SNP.
- Genotype-to-dose claims need CPIC/DPWG-level support; otherwise label the inference. When dosing is requested, cite the appropriate guideline or study, keeping prescription guidance and supplement evidence distinct.

## Evidence type and certainty

Report source design separately from claim-specific certainty. A guideline is a recommendation source; trace its underlying evidence and grading before using it to establish efficacy. A review's label or a trial's sample size alone does not determine support for this population and outcome.

For an intervention evidence synthesis, assess the body of evidence for each consequential outcome: bias, consistency, directness, precision and possible publication bias. Explain the reasons for confidence or uncertainty. If using formal GRADE labels, apply its method rather than treating document types as numbered quality grades. See [Cochrane Handbook, chapter 14](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14).

Record the relevant design details once: sample size, population match, controls/blinding, registration, funding/COI, independent replication, effect size and endpoint. Compare strong contradictory and null results as well as positive findings. For clinical decisions with high stakes, obtain an independent assessment of the same sources; a second model's agreement does not replace source verification.

## Inference and output

Label inference and state the assumptions that matter. For a quantitative inference, show the necessary derivation with units and examine plausible changes in the assumptions when they could change the conclusion. Qualitative reasoning does not need invented numerical sensitivity.

Keep evidence, inference and practical considerations distinguishable in the format the answer needs. Include access, cost, formulation or dosage only when requested or decision-relevant. Operational availability never establishes efficacy. A single concise evidence comparison can supply the study details for the synthesis; do not recite every source again or require a fixed three-section response.

## Relevant failure checks

Use the checks that apply to the current claim:

- **Genotype-to-phenotype leap:** do not turn a small association into a deterministic prediction.
- **Concentration confusion:** compare an in-vitro concentration with achievable human exposure before claiming transfer.
- **Funding/publication bias:** inspect study design and endpoint; funding is context, not an automatic verdict.
- **Authority substitution:** trace a personality's protocol or a guideline's efficacy assertion to supporting studies.
- **N=1 extrapolation:** a personal anecdote does not establish a population treatment effect.
- **False binaries and direction errors:** retain the source's effect size, uncertainty, affected moiety and direction.
- **Inference promotion:** a plausible mechanism stays an inference until the target outcome has direct support.
- **Genotype-only search:** for a proposed intervention, also search the condition and relevant clinical outcome.

Verify decisive numbers and cited studies, applicable genetic/dosing support, relevant counterevidence and material uncertainty before delivering. Do not manufacture checklist sections for claims the answer does not contain.

## Interpretation changes in a system

Before making a new runtime concept, check its actual caller and whether it changes a decision, escalation, contradiction handling or follow-up. A caveat that only renames or limits an existing concept belongs in the existing representation or memo. This applies when the authorized task includes system changes; a literature question alone does not trigger a design exercise.

## Other evidence and specialized authorities

Regulatory labels, safety communications, registries, preprints, independent product tests and supply-chain records can support the claims they actually measure. Label source type and limits. Product composition or formulation evidence does not substitute for clinical outcomes.

For PGx, use applicable CPIC/DPWG guidance and PharmGKB evidence levels. ClinVar, ClinGen and gnomAD answer different variant questions; cite the relevant record and version. No unsupported single-GWAS-hit or nutrigenomic dose leap.

## History and correction

The [historical guide](history.md) preserves all earlier incident/model notes, including the old 1–9 document hierarchy and mandatory recitation template. On 2026-09-05, the Astra guidance audit found that those rules conflated source type with certainty and expanded unrelated work. Current guidance grades support for the actual claim and uses only relevant verification. Dated GPT/Claude/Gemini error rates are historical observations, not measurements of today's models.
