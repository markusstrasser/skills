---
name: clingen-allele-registry-skill
description: Resolve canonical allele IDs (CAids) for variants via the ClinGen Allele Registry. Use when normalizing a variant across dbSNP / ClinVar / gnomAD / MyVariant before downstream lookups.
---

## Operating rules
- Use `scripts/clingen_allele_registry.py` for all Allele Registry calls.
- The Allele Registry assigns a canonical ID (`CA…`) per variant and returns cross-references to dbSNP, ClinVar, gnomAD, MyVariant, COSMIC, and others — use it to disambiguate before fanning out.
- Query by HGVS (preferred) or by CA ID. HGVS may be genomic (`NC_…:g.…`), coding (`NM_…:c.…`), or protein (`NP_…:p.…`). The registry resolves across builds.
- Read access is unauthenticated; write/registration paths require login and are out of scope here.
- Re-run lookups in long sessions instead of relying on stale results.

## Execution behavior
- Default: return a compact summary with `caid`, `genomicAlleles` (build, chrom, pos, ref, alt), and `externalRecords` keys (dbSNP, ClinVar, MyVariant, gnomAD).
- Set `save_raw=true` to write the full JSON-LD payload to a file and only return the path + top-level keys.
- HGVS that fails to resolve returns `ok=false` with `error.code=not_found`.

## Input
- One JSON object on stdin. Provide one of:
  - `hgvs`: HGVS string (genomic / coding / protein)
  - `ca_id`: existing canonical allele ID (e.g. `CA123456`)
- Optional: `max_items` (default 8), `max_depth` (default 3), `timeout_sec` (default 30), `save_raw` (bool), `raw_output_path` (string).

## Output
- Success: `{ok: true, source: "clingen-allele-registry", caid, summary, raw_output_path?}`.
- Failure: `{ok: false, error: {code, message}}`. Codes: `invalid_input`, `not_found`, `network_error`, `invalid_response`.

## Execution
```bash
echo '{"hgvs":"NC_000019.10:g.44908684T>C"}' | python3 scripts/clingen_allele_registry.py
echo '{"ca_id":"CA123456"}' | python3 scripts/clingen_allele_registry.py
```

## References
- API: https://reg.clinicalgenome.org/redmine/projects/registry/genboree_registry/landing
- Endpoint: `https://reg.clinicalgenome.org/allele?hgvs=...` and `/allele/{CA_ID}`
