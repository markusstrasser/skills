---
name: bio-verify
description: Verify hardcoded biological constants in Python scripts and config JSON against authoritative sources (Ensembl, ClinVar, ISBT, gnomAD, PanelApp). Dispatches parallel verification agents by domain. Use when auditing scripts with genomic coordinates, gene lists, risk ratios, or clinical classifications. Triggers on "verify claims", "fact-check script", "bio-verify", "check constants".
argument-hint: "[file or glob] [--domain nutrigenomics|blood|hla|traits|carrier|pgx|all] [--fix] [--sweep]"
effort: high
---

# Bio-Verify — Hardcoded Biological Claim Verification

Systematic sweep of Python scripts and config files for hardcoded biological claims, cross-checked against authoritative APIs. Empirical error rate: ~10-15% of manually-entered constants have detectable errors. Coordinates and ref/alt alleles are the highest-error category. Config JSON files have higher error rates than scripts.

**This skill produces an audit report.** Fixes are applied only if `--fix` is specified or user confirms.

## Claim Taxonomy

Scripts and configs embed these claim types, ordered by verification priority:

| Type | Example | Verification source | Failure mode |
|------|---------|-------------------|-------------|
| **Genomic position** | `chr12:47879112` | `variants_lookup` (dbSNP), `population_variant_frequency` (gnomAD r4) | Silent lookup miss — wrong position returns no data |
| **Ref/alt alleles** | `ref="C", alt="T"` | gnomAD r4 (definitive for GRCh38), dbSNP | Silent lookup miss — wrong alleles never match VCF |
| **rsID ↔ position** | `rs2228570 → chr12:47879112` | `variants_lookup` | Wrong variant entirely |
| **Gene coordinates** | `("chr9", 4985028, 5128183)` | `genetics_ensembl_gene` | Gene body not fully covered → exons missed |
| **Gene name** | `gene="BCMO1"` | `genetics_ensembl_gene`, `genetics_gene_info` | Stale name (BCMO1→BCO1), wrong gene at locus |
| **Gene list membership** | `ACMG_SF_GENES = [...]` | `curation_gene_validity`, `panels_panel_genes` | Missing genes, extra genes, wrong version. Count can be coincidentally correct with wrong composition |
| **Disease association** | `"disease": "CPEO"` | MITOMAP, ClinVar, OMIM, `rare_disease_gene_rare_diseases` | Wrong disease for variant/gene |
| **UPD / imprinting** | `"maternal_upd": "MODY"` | GeneReviews, literature | Wrong parent-of-origin → disease mapping |
| **Risk ratio / effect size** | `"3x risk"`, `"OR ~4.5"` | `gwas_variant_associations`, `verify_claim` (Exa) | Inflated/outdated/wrong-population estimate |
| **Inheritance mode** | `inheritance="AR"` | `rare_disease_gene_rare_diseases`, `curation_gene_validity` | XL misclassified as AR, etc |
| **Drug-gene interaction** | `"poor metabolizer"` | `targets_pharmacogenetics`, `drugs_star_alleles`, BioMCP `get pgx` (CPIC/PharmGKB) | Wrong phenotype, outdated CPIC guideline |
| **Oncology variant** | `"oncogenic"`, `"V600E tier 1"` | BioMCP `get variant BRAF V600E` (OncoKB/CIViC/CGI) | Wrong evidence level, missing therapy implications |
| **CGI drug association** | `"level A association"` | `composite_variant_context` (CGI field from MyVariant) | Wrong evidence level or tumor type |
| **COSMIC context** | `"high frequency in melanoma"` | `composite_variant_context` (COSMIC field from MyVariant) | Wrong tumor site or frequency |
| **Literature citation** | `PMID 28940476` | `verify_claim`, web search | Wrong PMID for claimed finding, sensitivity/specificity swapped |
| **Blood group antigen** | `Kell: K/k` | `bloodgroups_alleles`, `bloodgroups_search_alleles` | Wrong antigen assignment, missing alleles |

## Workflow

### Step 0: Parse arguments

```
/bio-verify scripts/modal_nutrigenomics.py           # Single file
/bio-verify scripts/blood_*.py                        # Glob
/bio-verify --sweep                                   # All scripts + configs with bio constants
/bio-verify scripts/trait_variant_panel.py --fix       # Verify and auto-fix
/bio-verify --domain blood                            # Only blood group claims
```

No arguments = `--sweep` (scan all `scripts/*.py` AND `config/*.json` for files containing bio constants).

### Step 1: Identify target files

If `--sweep`, find files containing hardcoded biological claims. **Scan both scripts and config JSON:**

```bash
# Scripts AND config files with variant dicts, gene lists, coordinate tuples, rsIDs
grep -rlE '(rs[0-9]{4,}|chr[0-9XY]+:[0-9]|"ref"|"alt"|ACMG|gnomAD|ClinVar|HDFN|severity|inheritance|"chrom"|"pos"|"gene")' scripts/*.py config/*.json \
  | grep -v modal_utils | grep -v __pycache__ | grep -v pipeline_stages | grep -v pipeline_cli
```

Exclude: `modal_utils.py` (config only), `pipeline_stages.py` / `pipeline_cli.py` (DAG metadata), `*_benchmark.py` (test data), external catalogs (e.g., `expansion_hunter_catalog_grch38.json` — unmodified Broad catalog).

**Config files often have higher error rates than scripts** (blood_type_panel.json was 80% wrong in the 2026-03-21 sweep). Prioritize configs with coordinates.

### Step 2: Extract claims from each file

Read each target file. Extract hardcoded biological claims by scanning for:

- **Variant dicts**: Dicts with keys like `rsid`, `chrom`/`chr`, `pos`, `ref`, `alt`, `gene`
- **Gene coordinate tuples**: `("chr9", 4985028, 5128183)` — gene region definitions
- **Gene lists**: Lists/sets of gene symbols (usually UPPER_CASE, 3-10 chars)
- **Coordinate tuples/strings**: `chrN:NNNNN` patterns, `(chrom, start, end)` tuples
- **Disease associations**: `"disease": "..."` in variant/gene dicts
- **Risk/effect claims**: Strings containing `"Nx risk"`, `"~N% reduced"`, `"odds ratio"`, `"OR="`, `"RR="`
- **Classification constants**: `severity=`, `inheritance=`, `classification=`, `stars=`
- **Drug interaction claims**: `"poor metabolizer"`, `"intermediate"`, `"ultrarapid"`, CPIC levels
- **Literature citations**: PMIDs, DOIs, author-year references
- **Sensitivity/specificity claims**: Percentages attributed to papers

For each claim, record: `{file, line, type, claimed_value, context_snippet}`.

**Important:** Include actual data samples from the file (first 2-3 entries of any dict/list) in agent prompts. Schema descriptions alone produce wrong field-name assumptions.

### Step 3: Route claims to verification domains

Group extracted claims by verification method:

| Domain | Claims routed here | Primary MCP tools |
|--------|-------------------|-------------------|
| **coordinates** | positions, ref/alt, rsID mappings, gene regions | `variants_lookup`, `population_variant_frequency`, `genetics_ensembl_gene` |
| **genes** | gene names, gene lists, gene-disease associations | `genetics_ensembl_gene`, `genetics_gene_info`, `curation_gene_validity` |
| **panels** | curated gene panel membership, ACMG-SF genes | `panels_panel_genes`, `panels_gene_panels`, web search |
| **disease** | disease associations, UPD conditions, MITOMAP | `verify_claim`, `rare_disease_gene_rare_diseases`, web search |
| **risk** | effect sizes, odds ratios, prevalence, sensitivity/PPV | `gwas_variant_associations`, `verify_claim` |
| **clinical** | ClinVar classifications, severity tiers | `variants_clinvar`, `composite_variant_context` |
| **inheritance** | AR/AD/XL mode claims | `rare_disease_gene_rare_diseases`, `curation_gene_validity` |
| **pgx** | drug-gene interactions, metabolizer status, CYP pathways | `targets_pharmacogenetics`, `drugs_star_alleles`, BioMCP `get pgx <gene> recommendations` (CPIC/PharmGKB), FDA DDI tables |
| **oncology** | oncogenic classifications, therapy levels, somatic evidence | BioMCP `get variant <variant>` (OncoKB/CIViC/cBioPortal), `composite_variant_context` (CGI/COSMIC from MyVariant) |
| **citations** | PMIDs, DOIs, author-year claims | `verify_claim`, web search |
| **blood** | blood group antigens, HDFN risk | `bloodgroups_alleles`, `bloodgroups_search_alleles`, `bloodgroups_systems` |

### Step 4: Dispatch verification agents

Dispatch parallel subagents, one per domain (or batched if domains are small). Each agent gets:

1. The claim list for its domain (with file paths, line numbers, and actual data samples)
2. Instructions to use specific MCP tools (listed above)
3. Output format: verification table (see below)
4. Instruction to write results to `docs/audit/biomedical-fact-check-YYYY-MM-DD/<domain>-verification.md`

**Agent dispatch template:**

```
CRITICAL: Stop all searching by your 18th tool call and write your synthesis.

Verify the following {domain} claims from the genomics pipeline.
For each claim, check against the authoritative source using the MCP tools listed.

Claims to verify:
{claim_list_with_file_line_context}

For EACH claim, fill in this row:
| rsID/Gene/Item | Claimed value | Verified value | Match? | Source tool | Impact if wrong | Fix |

Use these MCP tools:
{tool_list_for_domain}

IMPORTANT:
- For coordinates: gnomAD r4 is the ground truth for GRCh38. If variants_lookup returns hg19 in the dbSNP field, do NOT compare hg19 to GRCh38.
- For ref/alt: Always verify the GRCh38 reference allele. Strand inversions are common errors.
- For gene names: Check if the gene was renamed (e.g., BCMO1→BCO1). Old names aren't errors if the script's logic works, but flag for update.
- For gene lists: Check COMPOSITION not just count. A list can have the right count but wrong genes.
- For gene regions: Compare Ensembl gene body to claimed start/end. The claimed region should fully contain the gene.
- For citations: Verify the PMID/DOI exists AND matches the claimed content. Watch for sensitivity/specificity/PPV swaps.

Write your full report to: docs/audit/biomedical-fact-check-{date}/{domain}-verification.md
Include tool provenance (which MCP tool returned each answer).
```

**Parallelism:** Dispatch as many agents as needed — batch small domains together to keep total agent count reasonable. No fixed cap; use judgment based on MCP server load.

### Step 5: Collate results

After all agents complete:

1. Read each `docs/audit/biomedical-fact-check-YYYY-MM-DD/<domain>-verification.md`
2. Count: total claims checked, errors found, error rate by type
3. Categorize errors by severity:
   - **CRITICAL**: Wrong position or ref/alt → silent VCF lookup failure (data loss)
   - **HIGH**: Wrong gene list membership → false negatives in screening. Wrong disease association → incorrect clinical annotation
   - **MEDIUM**: Outdated gene name, imprecise risk estimate, wrong PMID, gene region partially truncated
   - **LOW**: Minor gene annotation (MCM6 vs LCT), acceptable shorthand, legacy nomenclature
4. Write `SYNTHESIS.md` with error summary, root cause analysis, and fix list

### Step 6: Fix (if requested)

If `--fix` or user confirms:

1. Apply fixes grouped by file (one Edit batch per file)
2. After fixing, run `ruff check --select F821,F601` on modified files
3. For coordinate/ref/alt fixes: verify the fix by running a re-verification agent to confirm new values are correct GRCh38
4. Commit with: `[curation] Fix N hardcoded bio constants — bio-verify audit YYYY-MM-DD`
   - `Evidence: docs/audit/biomedical-fact-check-YYYY-MM-DD/`

### Step 7: Re-verify fixes

After applying fixes, dispatch a lightweight re-verification agent to confirm each corrected value is actually correct. This catches transcription errors in the fix itself. Round 4 of the 2026-03-21 sweep found 0 errors in re-verification — fixes from MCP APIs are reliable, but the check is cheap.

### Step 8: Decision journal (if errors found)

If errors were found and fixed, write a decision journal entry:

```markdown
# Bio-Verify Audit YYYY-MM-DD

**Trigger:** /bio-verify sweep
**Scope:** N files, M claims checked
**Errors:** X found (Y% error rate)
**Error types:** [position: N, ref/alt: N, gene name: N, ...]
**Root cause:** [manual entry without cross-check, liftover errors, stale gene names, ...]
**Fix:** Corrected in commit [hash]
```

### Step 9: Update tracking state

After verification (whether errors were found or not), update the bio-verify state file:

```bash
uv run python scripts/bio_verify_status.py --update <filepath> <YYYY-MM-DD> [errors_found] [audit_path]
```

For each file verified in this session:
```bash
uv run python scripts/bio_verify_status.py --update scripts/generate_pgx_card.py 2026-03-24 0 docs/audit/biomedical-fact-check-2026-03-24/pgx-card-verification.md
```

This feeds the `/maintain` rotation queue. Run `just bio-verify-queue` to see what's next.

When using `--sweep`, also run `just bio-verify-status` at the end to show overall coverage.

## Known Issues
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

## Prior Audit Results (calibration)

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

## Complementary Checks

Bio-verify checks **data correctness** (are biological constants accurate?). Two complementary systems check **logic correctness**:

- **Canary gate** (`just canary` in genomics) — 55 sentinel variants through `auto_classify()`. Catches classification logic regressions. Runs as pre-commit hook on classification file changes.
- **Calibration canaries** (`meta/scripts/calibration-canary.py`) — 47 boolean questions testing model calibration. Weekly via `/maintain`. Not genomics-specific but measures the trustworthiness of LLM judgments used elsewhere in the pipeline.
