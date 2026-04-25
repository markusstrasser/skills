---
name: gnomad-sv-skill
description: gnomAD-SV v4 GraphQL — population frequencies for structural variants (DEL / DUP / INV / INS / BND / CPX). Use when interpreting a DELLY / Manta / pangenie call against population SV background. Distinct from the SNV gnomAD skill.
---

## Operating rules
- Use `scripts/gnomad_sv.py`.
- The endpoint is the same Broad server as the SNV API (`gnomad.broadinstitute.org/api`), but the query type is `structural_variant` (not `variant`). Do not reuse `gnomad-graphql-skill` queries.
- Variant IDs follow the pattern `<TYPE>_chr<chrom>_<id>` (e.g. `DEL_chr1_0001`). Query by `variantId` for a single variant or by `gene_symbol` / `region` for cohort views.
- Datasets: `gnomad_sv_r4` (current). Older `gnomad_sv_r2_1` exists for back-compat.
- For nested GraphQL results, start with `max_items=3` to `5`. Use `query_path` for long inline queries.
- Population AF in SVs is more sensitive to filter status than SNVs — always carry the `filters` array in the answer.

## Execution behavior
- `mode=variant`: lookup one SV by `variantId`.
- `mode=region`: list SVs overlapping a region (`chrom`, `start`, `stop`, optional `referenceGenome`).
- `mode=gene`: list SVs overlapping a gene by symbol.
- `mode=raw`: arbitrary GraphQL document.

## Input
- One JSON object on stdin.
- Required: `mode` ∈ {`variant`, `region`, `gene`, `raw`}.
- `mode=variant`: `variantId`.
- `mode=region`: `chrom`, `start`, `stop`. Optional `referenceGenome` (default `GRCh38`).
- `mode=gene`: `gene` (HGNC symbol).
- `mode=raw`: `query` (GraphQL string), optional `variables`.
- Optional: `dataset` (default `gnomad_sv_r4`), `max_items`, `max_depth`, `timeout_sec`, `save_raw`, `raw_output_path`.

## Output
- Success: `{ok: true, source: "gnomad-sv", mode, summary, raw_output_path?}`.
- Failure: `{ok: false, error: {code, message}}`.

## Execution
```bash
echo '{"mode":"variant","variantId":"DEL_chr1_0001"}' | python3 scripts/gnomad_sv.py
echo '{"mode":"region","chrom":"1","start":1000000,"stop":1100000}' | python3 scripts/gnomad_sv.py
echo '{"mode":"gene","gene":"BRCA1"}' | python3 scripts/gnomad_sv.py
```

## References
- Endpoint: https://gnomad.broadinstitute.org/api
- Docs: https://gnomad.broadinstitute.org/api (schema browser)
- Background: gnomAD-SV v4 paper / release notes on broadinstitute.org
