# selve Claim Patterns

When `/bio-verify` runs from selve CWD (`~/Projects/selve/`), the claim surface is different from genomics. Run the local consistency script first, then use agent sweep for external validation.

## Pre-flight

```bash
uv run python3 scripts/verify_pgx_consistency.py
```

This runs 12 local checks (no API calls, ~5s) covering internal consistency, CPIC activity scores, and phenoconversion. Fix any errors before launching agent verification.

## Claim Surface

| Source | File(s) | Claim types | Count |
|--------|---------|-------------|-------|
| Gene entity pages | `docs/entities/genes/*.md` (22 files) | Diplotype, phenotype, activity score, CPIC level, drug interactions (Drug/Category/Effect/Guideline/Action table), dose adjustments, PMIDs | ~200 claims |
| Genomics findings YAML | `docs/entities/self/genomics_findings.yaml` | Diplotype, phenotype, activity_score, source, drugs_affected per gene | 35 entries |
| PGx graph | `indexed/pgx.duckdb` | Drug→enzyme edges with sign (±1), relation, weight, evidence | 19,564 edges |
| PharmGKB | `indexed/pharmgkb_parsed.json` | Gene-drug pairs with evidence level (1A-4) | 395 entries |
| Medical ledger | `indexed/medical_data.duckdb` | Active medications, conditions, lab values | ~400 entries |

## Extraction Patterns

### Entity page YAML frontmatter
```yaml
title, date, last_reviewed, review_cadence, coverage, tags, status,
derived_from, verification, summary
```
The `summary` field contains the diplotype and phenotype in prose.

### Entity page drug interaction table
```markdown
| Drug | Category | Effect for IM | Guideline | Action |
```
Extract: drug name, CPIC/DPWG guideline + year, dosing action.

### Entity page inline citations
Format: `PMID 32476266`, `DOI 10.1002/cpt.3351`
Extract with regex: `PMID\s+\d+`, `DOI\s+[\d./\w-]+`

### Genomics findings YAML per-gene entry
```yaml
gene, diplotype, phenotype, activity_score, source, drugs_affected,
clinical_note, research_memo, entity_page
```

### PGx graph edge schema
```sql
source TEXT, target TEXT, relation TEXT, sign INTEGER, weight REAL,
evidence TEXT, pmid TEXT, notes TEXT
```
Key: `sign=+1` for prodrug activation, `sign=-1` for active drug clearance.

## Agent Verification Routing (external checks)

When running a bio-verify agent sweep on selve, route claims to these domains:

| Domain | Claims | Primary MCP tools |
|--------|--------|-------------------|
| pgx-relationships | Drug→enzyme edges, metabolizer status | `targets_pharmacogenetics`, CPIC API, `normalize_drug` |
| dose-adjustments | "2x AUC", "25% dose reduction" | `verify_claim` (Exa), CPIC guidelines |
| phenotype-assignments | "Intermediate Metabolizer", activity scores | CPIC activity score tables, `drugs_star_alleles` |
| entity-citations | PMIDs, DOIs in gene entity pages | `verify_claim`, `literature_variant_publications` |

## Known Issues (selve-specific)

1. **Diplotype format varies**: Star notation (*1/*4) for CYP genes, rs notation for VKORC1, protein change (p.Met207Thr) for G6PD. Parser handles star + table format; rs/protein formats fall through as warnings.
2. **Phenotype qualifiers**: YAML may have extra context (e.g., "Poor Metabolizer (Gilbert syndrome)") vs entity page ("Poor Metabolizer"). Comparison strips parenthetical qualifiers.
3. **Active medications without PGx graph coverage**: semaglutide, tirzepatide, daridorexant, trazodone have no graph edges (as of 2026-04-07). These are real gaps, not parsing errors.
4. **Prodrug edge signs**: Codeine (+1, activation), metoprolol (-1, clearance). See `config/prodrug_annotations.json`.
