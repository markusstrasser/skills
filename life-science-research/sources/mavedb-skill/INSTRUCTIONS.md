---
name: mavedb-skill
description: Query MaveDB for multiplexed assay variant-effect (MAVE / DMS) score sets and per-variant functional scores. Use when a variant question needs experimental fitness evidence beyond computational predictors.
---

## Operating rules
- Use `scripts/mavedb.py` for all MaveDB calls.
- MaveDB hosts curated DMS / MAVE assays; each "score set" is a single experiment with per-variant scores. Variants are mapped to GRCh38 + ClinGen CAids in modern entries.
- Search by gene symbol or UniProt accession to find score sets. Resolve a score set URN (`urn:mavedb:00000…`) before pulling variants.
- Read endpoints are unauthenticated; write/upload requires an API key (out of scope here).
- For bulk benchmark needs, prefer the Zenodo bulk archive over per-URN walks.

## Execution behavior
- `mode=search`: list score sets matching a gene / UniProt, returning URN, title, target gene, and assay summary.
- `mode=score_set`: fetch one score set by URN with metadata, scoring model, and a sample of mapped variants.
- `mode=variants`: page through mapped variants for one URN (compact, with score column).
- Set `save_raw=true` to dump the full JSON to a file.

## Input
- One JSON object on stdin.
- Required: `mode` ∈ {`search`, `score_set`, `variants`}.
- For `mode=search`: `gene` (HGNC symbol) OR `uniprot` accession.
- For `mode=score_set` / `mode=variants`: `urn` (e.g. `urn:mavedb:00000001-a-1`).
- Optional: `limit` (default 20 for search/variants), `max_items`, `max_depth`, `timeout_sec`, `save_raw`, `raw_output_path`.

## Output
- Success: `{ok: true, source: "mavedb", mode, summary, raw_output_path?}`.
- Failure: `{ok: false, error: {code, message}}`. Codes: `invalid_input`, `not_found`, `network_error`, `invalid_response`.

## Execution
```bash
echo '{"mode":"search","gene":"BRCA1"}' | python3 scripts/mavedb.py
echo '{"mode":"score_set","urn":"urn:mavedb:00000097-0-1"}' | python3 scripts/mavedb.py
echo '{"mode":"variants","urn":"urn:mavedb:00000097-0-1","limit":10}' | python3 scripts/mavedb.py
```

## References
- API root: https://api.mavedb.org/api/v1/
- Bulk archive (Zenodo): search "MaveDB" — preferred for benchmarks
- Schema: https://www.mavedb.org/docs/
