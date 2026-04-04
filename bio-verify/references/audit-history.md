<!-- Reference file for bio-verify skill. Loaded on demand. -->

# Prior Audit Results (calibration)

| Date | Scope | Claims | Errors | Rate | Worst domain |
|------|-------|--------|--------|------|-------------|
| 2026-03-21 | nutrigenomics | 20 | 6 | 30% | ref/alt (5 wrong) |
| 2026-03-21 | traits | 40 | 5 | 12.5% | positions |
| 2026-03-21 | blood groups (Kell/Duffy/Kidd) | 16 | 0 | 0% | — |
| 2026-03-21 | HLA/CH | ~15 | 2 | 13% | coordinates |
| 2026-03-21 | reproductive | 55 | 9 | 16.4% | mixed |
| 2026-03-21 | HIrisPlex SNPs | 41 | 0 | 0% | — |
| 2026-03-21 | blood type panel | 5 | 4 | 80% | coordinates (config JSON) |
| 2026-03-21 | QC spotcheck | 10 | 2 | 20% | hg19 coordinate |
| 2026-03-21 | ACMG SF v3.3 gene list | 84 | 16 | 19% | composition (8 extra + 8 missing) |
| 2026-03-21 | mito phylogenetics | 23 | 0 | 0% | — |
| 2026-03-21 | carrier screening genes | 38 | 0 | 0% | — |
| 2026-03-21 | MITOMAP pathogenic | 37 | 2 | 5.4% | disease association |
| 2026-03-21 | CHIP gene coords | 28 | 5 | 17.9% | truncated gene regions + citation swap |
| 2026-03-21 | PGx pathways | ~30 | 1 | 3.3% | wrong PMID |
| 2026-03-21 | imprinted regions | 7 | 2 | 28.6% | wrong UPD disease (GNAS) |
| 2026-03-21 | penetrance estimates | 5 | 0 | 0% | — |
| 2026-03-25 | archaic functional map | 11 | 3 | 27% | gnomAD AF values |
| 2026-03-25 | nutrient absorption | 9 | 0 | 0% | — |
| 2026-03-25 | anesthesia risk card | 7 | 0 | 0% | — |
| 2026-03-25 | pathogen susceptibility | 8 | 0 | 0% | — |
| 2026-03-25 | predicted proteins | 10 | 11 | 110% | positions (hg19) + effect alleles |
| 2026-03-25 | imprinting ICRs | 6 | 0 | 0% | — |
| 2026-03-25 | connective tissue genes | 14 | 0 | 0% | — |
| 2026-03-25 | digenic pairs | 10 | 1 | 10% | PMID mismatch |
| **TOTAL** | **all sweeps** | **~529** | **~69** | **~13%** | coordinates, AFs, gene lists |

**Baseline expectation:** ~10-15% of manually-entered biological constants contain errors detectable by API cross-check. Coordinates/positions are the highest-error category. Config JSON files have higher error rates than scripts. Error rate drops to 0% after one fix-and-recheck cycle.
