---
name: source-grading
description: NATO Admiralty System for grading source reliability and information credibility. Apply automatically during OSINT, forensic investigations, legal research, entity audits, or fraud analysis — NOT for general software or casual research. Every claim gets a 2-axis grade (A-F for source reliability, 1-6 for information credibility).
user-invocable: false
model: haiku
---

# Source Grading: The Admiralty System

Every claim in research or investigation output must be graded on two independent axes.

## Axis 1: Source Reliability (Who provided this?)

| Grade | Label | Criteria | Examples |
|-------|-------|----------|----------|
| **A** | Completely Reliable | Proven track record; legally accountable for falsehood | Court records, SEC filings, government audit reports, enforcement actions |
| **B** | Usually Reliable | Institutional reputation at stake; editorial/peer review | Academic peer-reviewed studies, major investigative journalism, GAO/OIG reports |
| **C** | Fairly Reliable | Domain expertise but potential bias; less rigorous review | Trade press, industry reports, state agency press releases |
| **D** | Not Usually Reliable | Self-interested; no independent verification | Company press releases, PR, marketing, self-reported data |
| **E** | Unreliable | Known bias, history of inaccuracy, no accountability | Social media, anonymous forums, unverified tips |
| **F** | Cannot Be Judged | Source reliability cannot be assessed | New/unknown source, automated data with unknown provenance |

## Axis 2: Information Credibility (Is this claim true?)

| Grade | Label | Criteria |
|-------|-------|----------|
| **1** | Confirmed | Independently verified by 2+ sources from different domains |
| **2** | Probably True | Consistent with known data; one independent confirmation |
| **3** | Possibly True | No confirmation, no contradiction; plausible but unverified |
| **4** | Doubtful | Inconsistent with some known data; requires assumptions |
| **5** | Improbable | Contradicted by known data or independent sources |
| **6** | Cannot Be Judged | Not enough information to assess truth value |

## Combined Grade Format

Write grades as `[Grade: X#]` inline with claims:

- "ABI owes $14.3M in wage theft" **[A1]** — Crain's (A), confirmed by DOL records (1)
- "The entity has no web presence" **[F3]** — absence of evidence (F), possibly true (3)
- "$1.68B in Medicaid billing" **[A1]** — CMS official data (A), cross-verified (1)

## Rules

1. **Grade source and information independently.** A completely reliable source (A) can report wrong information (4-5). An unreliable source (E) can provide independently confirmed information (1).

2. **Upgrade credibility when sources converge.** Three C-grade sources independently reporting the same fact → credibility upgrades toward 1-2.

3. **Downgrade credibility when sources share upstream.** Three sources citing the same original report = ONE source, not three.

4. **Absence of evidence is not evidence of absence.** "No enforcement action found" is [B3] at best.

5. **Self-interested sources get automatic D.** Company statements about their own compliance, self-attestation, marketing — never above D unless independently confirmed.

6. **Data from our own analysis is [DATA].** A-reliability (official source), credibility depends on query correctness.

## Integration with Provenance Tags

| Old Tag | Admiralty Equivalent |
|---------|---------------------|
| [DATA] | [DATA] (keep — indicates own analysis) |
| [SOURCE: url] | [Grade: X#] with the URL |
| [INFERENCE] | [INFERENCE: X# + X#] — cite grades of premises |
| [UNCONFIRMED] | Any claim graded 3-6 on credibility |

## When to Grade

- **Always** during `investigate` or `researcher` workflows
- **Always** in analysis documents for handoff (attorneys, journalists, government)
- **Optional** in informal conversation or brainstorming
- **Required** before any lead enters the diagnosticity matrix in `competing-hypotheses`
