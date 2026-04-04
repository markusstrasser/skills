<!-- Reference file for bio-verify skill. Loaded on demand. -->

# Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->

1. **`variants_lookup` returns hg19 in the dbSNP field** — Never compare hg19 positions to GRCh38 claims. Use `population_variant_frequency` (gnomAD r4) for definitive GRCh38 coordinates.
2. **gnomAD doesn't index every variant** — Some valid variants (especially non-coding regulatory) are absent from gnomAD. Use `verify_claim` (Exa) as fallback, but note it's lower confidence.
3. **Gene renaming is common** — BCMO1→BCO1, GBA→GBA1, MUT→MMUT. Check Ensembl for canonical current name. Old names in scripts are low-severity unless they break lookups.
4. **ISBT blood group nomenclature** — Use `bloodgroups_search_alleles` with both ISBT number and common name. Some alleles have multiple valid designations.
5. **Frequency-first for strand ambiguity** — When ref/alt could be strand-flipped, check gnomAD allele frequency. The common allele at the expected frequency resolves the ambiguity. (Lesson from Kell incident.)
6. **Gene list count ≠ correctness** — ACMG SF v3.3 list had 84 genes (correct count) but 16 were wrong (8 extra, 8 missing). Always verify composition, not just count.
7. **Config files > scripts for error rate** — `blood_type_panel.json` was 80% wrong. Configs are often assembled once from mixed sources without systematic cross-checking. Prioritize them.
8. **Assembly confusion clusters** — hg19 coordinates in a GRCh38 pipeline are the #1 error type. The ABO locus had non-standard offsets (neither clean hg19 nor hg38). Check for centromere/assembly-specific coordinate shifts.
9. **Citation content swaps** — Sensitivity and PPV/specificity get swapped when transcribing from papers. Verify the claim matches the paper's actual numbers, not just that the PMID exists.
10. **Paralog coordinate confusion** — RHD/RHCE (>95% homology) had RHCE coordinates used for RHD exon 7. Common in segmental duplication regions.
11. **CPIC API is authoritative for PGx Level A pairs** — `api.cpicpgx.org/v1/pair?cpiclevel=eq.A` joined with `/v1/drug` returns the canonical list (100 pairs as of 2026-03-24). Perplexity is unreliable here — scraped incomplete HTML tables and contradicted itself across queries. For PGx completeness checks, always use the API, not web search.
12. **GenCC classifications hallucination-prone via web search** — Perplexity fabricated "Definitive" GenCC classifications with fake dates for NOTCH3 and KRIT1. Only corrected after being shown contradicting ClinGen API data. For GenCC lookups, use `thegencc.org` directly or cross-check against `curation_gene_validity` results. Never trust a single web search answer for database classification lookups.
13. **Imprinted region DMRs span large domains** — Don't flag ICR/DMR coordinates as wrong based on distance from gene body alone. The DLK1-DIO3 domain spans ~1 Mb on chr14q32.2; the IG-DMR at chr14:101,290,000 is 430 kb from DLK1 but confirmed correct by ClinGen (ISCA-46745). Use ClinGen region lookups or `verify_claim` for ICR position verification, not gene body proximity.
14. **BioMCP available for PGx/oncology verification** — `biomcp` MCP server is configured alongside biomedical-mcp in genomics/selve. Use `biomcp get pgx <gene> recommendations` for CPIC verification and `biomcp get variant <gene> <change>` for OncoKB/CIViC evidence levels. BioMCP output is Markdown, not JSON — parse accordingly.
15. **Variant normalization supports gene+protein format** — `composite_variant_context` now accepts "BRAF V600E", "EGFR L858R", "BRAF p.Val600Glu" in addition to rsIDs and HGVS. Use this for protein-change claims in scripts.
16. **CGI/COSMIC now in variant_context output** — `composite_variant_context` extracts CGI drug associations and COSMIC somatic context from MyVariant responses. Check `cgi_drug_associations` and `cosmic` fields.
17. **Effect/archaic allele AF convention** — Some scripts track the AF of the effect/archaic allele, not the gnomAD alt allele. When `archaic_allele == ref`, the AF field = 1 - gnomAD_alt_AF. Before flagging an AF as wrong, check whether the script's convention matches the comparison. (rs5743618 false positive: script correctly reported ref allele C AF=0.726 = 1-0.274.)
