---
name: bio-verify
description: Verify hardcoded biological constants in Python scripts against authoritative sources (Ensembl, ClinVar, ISBT, gnomAD, PanelApp). Dispatches parallel verification agents by domain. Use when auditing scripts with genomic coordinates, gene lists, risk ratios, or clinical classifications. Triggers on "verify claims", "fact-check script", "bio-verify", "check constants".
argument-hint: "[file or glob] [--domain nutrigenomics|blood|hla|traits|carrier|pgx|all] [--fix]"
effort: high
---

# Bio-Verify — Hardcoded Biological Claim Verification

Systematic sweep of Python scripts for hardcoded biological claims, cross-checked against authoritative APIs. Prior runs found 16-30% error rates in coordinates and ref/alt alleles — these are silent data-loss bugs (VCF lookups return nothing, no error raised).

**This skill produces an audit report.** Fixes are applied only if `--fix` is specified or user confirms.

## Claim Taxonomy

Scripts embed these claim types, ordered by verification priority:

| Type | Example | Verification source | Failure mode |
|------|---------|-------------------|-------------|
| **Genomic position** | `chr12:47879112` | `variants_lookup` (dbSNP), `population_variant_frequency` (gnomAD r4) | Silent lookup miss — wrong position returns no data |
| **Ref/alt alleles** | `ref="C", alt="T"` | gnomAD r4 (definitive for GRCh38), dbSNP | Silent lookup miss — wrong alleles never match VCF |
| **rsID ↔ position** | `rs2228570 → chr12:47879112` | `variants_lookup` | Wrong variant entirely |
| **Gene name** | `gene="BCMO1"` | `genetics_ensembl_gene`, `genetics_gene_info` | Stale name (BCMO1→BCO1), wrong gene at locus |
| **Gene list membership** | `ACMG_SF_GENES = [...]` | `curation_gene_validity`, `panels_panel_genes` | Missing genes, extra genes, wrong version |
| **Risk ratio / effect size** | `"3x risk"`, `"~70% reduced"` | `gwas_variant_associations`, `verify_claim` (Exa) | Inflated/outdated/wrong-population estimate |
| **Severity / classification** | `severity="high"` | `variants_clinvar`, `curation_gene_validity` | Wrong ClinVar stars, wrong ACMG class |
| **Inheritance mode** | `inheritance="AR"` | `rare_disease_gene_rare_diseases`, `curation_gene_validity` | XL misclassified as AR, etc |
| **Drug-gene interaction** | `"poor metabolizer"` | `targets_pharmacogenetics`, `drugs_star_alleles` | Wrong phenotype, outdated CPIC guideline |
| **Blood group antigen** | `Kell: K/k` | `bloodgroups_alleles`, `bloodgroups_search_alleles` | Wrong antigen assignment, missing alleles |
| **Genomic coordinates (regions)** | `AZFa: Y:6200000-7100000` | `genetics_ensembl_gene` + literature | Shifted coordinates, wrong build |

## Workflow

### Step 0: Parse arguments

```
/bio-verify scripts/modal_nutrigenomics.py           # Single file
/bio-verify scripts/blood_*.py                        # Glob
/bio-verify --sweep                                   # All scripts with bio constants
/bio-verify scripts/trait_variant_panel.py --fix       # Verify and auto-fix
/bio-verify --domain blood                            # Only blood group claims
```

No arguments = `--sweep` (scan all `scripts/*.py` for files containing bio constants).

### Step 1: Identify target files

If `--sweep`, find scripts containing hardcoded biological claims:

```bash
# Files with variant dicts, gene lists, coordinate tuples, rsIDs
grep -rlE '(rs[0-9]{4,}|chr[0-9XY]+:|"ref"|"alt"|ACMG|gnomAD|ClinVar|HDFN|severity|inheritance)' scripts/*.py \
  | grep -v modal_utils | grep -v __pycache__
```

Exclude: `modal_utils.py` (config only), `pipeline_*.py` (DAG metadata), `*_benchmark.py` (test data).

### Step 2: Extract claims from each file

Read each target file. Extract hardcoded biological claims by scanning for:

- **Variant dicts**: Dicts with keys like `rsid`, `chrom`/`chr`, `pos`, `ref`, `alt`, `gene`
- **Gene lists**: Lists/sets of gene symbols (usually UPPER_CASE, 3-10 chars)
- **Coordinate tuples/strings**: `chrN:NNNNN` patterns, `(chrom, start, end)` tuples
- **Risk/effect claims**: Strings containing `"Nx risk"`, `"~N% reduced"`, `"odds ratio"`, `"OR="`, `"RR="`
- **Classification constants**: `severity=`, `inheritance=`, `classification=`, `stars=`
- **Drug interaction claims**: `"poor metabolizer"`, `"intermediate"`, `"ultrarapid"`, CPIC levels

For each claim, record: `{file, line, type, claimed_value, context_snippet}`.

**Important:** Include actual data samples from the file (first 2-3 entries of any dict/list) in agent prompts. Schema descriptions alone produce wrong field-name assumptions.

### Step 3: Route claims to verification domains

Group extracted claims by verification method:

| Domain | Claims routed here | Primary MCP tools |
|--------|-------------------|-------------------|
| **coordinates** | positions, ref/alt, rsID mappings | `variants_lookup`, `population_variant_frequency` |
| **genes** | gene names, gene lists, gene-disease associations | `genetics_ensembl_gene`, `genetics_gene_info`, `curation_gene_validity` |
| **panels** | curated gene panel membership, ACMG-SF genes | `panels_panel_genes`, `panels_gene_panels` |
| **risk** | effect sizes, odds ratios, prevalence claims | `gwas_variant_associations`, `verify_claim` |
| **clinical** | ClinVar classifications, severity tiers | `variants_clinvar`, `composite_variant_context` |
| **inheritance** | AR/AD/XL mode claims | `rare_disease_gene_rare_diseases`, `curation_gene_validity` |
| **pgx** | drug-gene interactions, metabolizer status | `targets_pharmacogenetics`, `drugs_star_alleles` |
| **blood** | blood group antigens, HDFN risk | `bloodgroups_alleles`, `bloodgroups_search_alleles`, `bloodgroups_systems` |

### Step 4: Dispatch verification agents

Dispatch parallel subagents, one per domain with claims. Each agent gets:

1. The claim list for its domain (with file paths, line numbers, and actual data samples)
2. Instructions to use specific MCP tools (listed above)
3. Output format: verification table (see below)
4. Instruction to write results to `docs/audit/biomedical-fact-check-YYYY-MM-DD/<domain>-verification.md`

**Agent dispatch template:**

```
Verify the following {domain} claims from the genomics pipeline scripts.
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
- For gene lists: Check completeness against the latest version of the source (ACMG SF v3.3, etc.)

Write your full report to: docs/audit/biomedical-fact-check-{date}/{domain}-verification.md
Include tool provenance (which MCP tool returned each answer).

Stop searching at 70% of turns and synthesize.
```

**Max 4 parallel agents** (MCP contention limit). If >4 domains have claims, batch the smaller domains together.

### Step 5: Collate results

After all agents complete:

1. Read each `docs/audit/biomedical-fact-check-YYYY-MM-DD/<domain>-verification.md`
2. Count: total claims checked, errors found, error rate by type
3. Categorize errors by severity:
   - **CRITICAL**: Wrong position or ref/alt → silent VCF lookup failure (data loss)
   - **HIGH**: Wrong gene list membership → false negatives in screening
   - **MEDIUM**: Outdated gene name, imprecise risk estimate
   - **LOW**: Minor gene annotation (MCM6 vs LCT), acceptable shorthand

### Step 6: Fix (if requested)

If `--fix` or user confirms:

1. Apply fixes grouped by file (one Edit batch per file)
2. After fixing, run `ruff check --select F821,F601` on modified files
3. For coordinate/ref/alt fixes: verify the fix by running `uv run python3 -c "..."` to confirm the corrected variant is findable in gnomAD
4. Commit with: `[curation] Fix N hardcoded bio constants — bio-verify audit YYYY-MM-DD`
   - `Evidence: docs/audit/biomedical-fact-check-YYYY-MM-DD/`

### Step 7: Decision journal (if errors found)

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

## Known Gotchas

1. **`variants_lookup` returns hg19 in the dbSNP field** — Never compare hg19 positions to GRCh38 claims. Use `population_variant_frequency` (gnomAD r4) for definitive GRCh38 coordinates.
2. **gnomAD doesn't index every variant** — Some valid variants (especially non-coding regulatory) are absent from gnomAD. Use `verify_claim` (Exa) as fallback, but note it's lower confidence.
3. **Gene renaming is common** — BCMO1→BCO1, MTHFR still MTHFR. Check Ensembl for canonical current name. Old names in scripts are low-severity unless they break lookups.
4. **ISBT blood group nomenclature** — Use `bloodgroups_search_alleles` with both ISBT number and common name. Some alleles have multiple valid designations.
5. **Frequency-first for strand ambiguity** — When ref/alt could be strand-flipped, check gnomAD allele frequency. The common allele at the expected frequency resolves the ambiguity. (Lesson from Kell incident.)

## Prior Audit Results (calibration)

| Date | Scope | Claims | Errors | Rate | Worst domain |
|------|-------|--------|--------|------|-------------|
| 2026-03-21 | nutrigenomics | 20 | 6 | 30% | ref/alt (5 wrong) |
| 2026-03-21 | traits | 40 | 5 | 12.5% | positions |
| 2026-03-21 | blood groups | 16 | 0 | 0% | — |
| 2026-03-21 | HLA/CH | ~15 | 2 | 13% | coordinates |
| 2026-03-21 | reproductive | 55 | 9 | 16.4% | mixed (coords, gene lists, severity) |

**Baseline expectation:** ~15-20% of manually-entered biological constants contain errors detectable by API cross-check. Coordinates and ref/alt alleles are the highest-error category.
