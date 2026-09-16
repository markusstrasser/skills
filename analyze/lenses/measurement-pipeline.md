# Measurement-Pipeline Lens

Use when the object is a published statistic built from administrative or survey records (crime,
deaths, cases, unemployment, incidents, migration, inequality) and the question is whether the number
can differ from the quantity it names, in which direction, and by how much. Run before any comparison
across groups, places or years, and before the null/base-rate lens: the number itself may be the artifact.

1. **Write the pipeline.** event → report → record → classification → disposition → count → denominator
   → aggregation → publication. Name the institution that controls each stage.
2. **At each stage ask four things:** who controls it; what is the residual category and who renamed it
   ("unknown/other" → native-born, "not identified as legal" → illegal, "non-resident" still in a
   resident-rate numerator); what changed in the window (definition, form, coverage, leadership); what is
   the sign on the published ratio.
3. **Date the extract.** Same-year numbers differ by pull date (late identification, revisions,
   right-censoring). Compare like vintage to like vintage; carry the extract date with the number.
4. **Recompute under the alternative construction.** Resident vs present denominator; with and without
   status offences; with and without the instrument change; both attributions of shared costs. The range
   across constructions is the headline, never the favorite endpoint.
5. **Keep contradictions.** Where a source contradicts the starting hypothesis, the contradiction is the
   finding. Do not drop it.
6. **Grade each mechanism** A–D by source and state one of: measured · real-in-law-but-unmeasured ·
   not found (absence verified by search, queries listed).

Output:

- pipeline table: stage · controller · residual category · change in window · sign · magnitude · grade
- the two largest measured errors, and whether they share a sign
- missing instruments (absences verified by search)
- the range across constructions, with the extract date

Adjunct: the construction checks in the research skill's `references/quant-bias-checklist.md`
(ledger, unit, base, window, gross/net, measurement-vs-model).

Origin: immigration-research `research/immigration-crime-statistics-bias-mechanisms-2026-09-16.md`
(38 candidate mechanisms over six stages, 12 grounded at grade A; the two largest measured errors
pointed in opposite directions).
