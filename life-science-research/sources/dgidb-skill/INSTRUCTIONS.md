---
name: dgidb-skill
description: DGIdb v5 GraphQL — drug-gene interactions aggregated across 40+ sources (ChEMBL, CKB, Drugs@FDA, NCI, etc.). Use when answering "what drugs target this gene" or "what genes does this drug hit" with source-aware evidence.
---

## Operating rules
- Use `scripts/dgidb.py` for all DGIdb v5 calls.
- DGIdb v5 is GraphQL-only (REST deprecated). Endpoint is unauthenticated.
- Query by gene symbol(s) or drug name(s); both accept lists. Cursor pagination is available; default `first=25`.
- Each interaction record carries source attribution and interaction types (inhibitor / agonist / antagonist / etc.) — surface these, don't strip them.
- DGIdb is target-discovery aggregation, not a clinical PGx source. For pharmacogenomics use PharmGKB / CPIC.
- For nested GraphQL results, start with `max_items=3` to `5`; expand only after seeing signal.

## Execution behavior
- `mode=genes`: drug-interaction lookup by gene symbol(s).
- `mode=drugs`: gene-interaction lookup by drug name(s) or ChEMBL ID.
- `mode=raw`: arbitrary GraphQL document (advanced).
- Default returns compact summary keyed by gene or drug; set `save_raw=true` for the full payload.

## Input
- One JSON object on stdin.
- Required: `mode` ∈ {`genes`, `drugs`, `raw`}.
- For `mode=genes`: `genes` (list of HGNC symbols).
- For `mode=drugs`: `drugs` (list of names or ChEMBL IDs).
- For `mode=raw`: `query` (GraphQL string), optional `variables`.
- Optional: `first` (page size, default 25), `max_items`, `max_depth`, `timeout_sec`, `save_raw`, `raw_output_path`.

## Output
- Success: `{ok: true, source: "dgidb", mode, summary, raw_output_path?}`.
- Failure: `{ok: false, error: {code, message}}`. Codes: `invalid_input`, `network_error`, `graphql_error`.

## Execution
```bash
echo '{"mode":"genes","genes":["BRAF","KRAS"]}' | python3 scripts/dgidb.py
echo '{"mode":"drugs","drugs":["IMATINIB"]}' | python3 scripts/dgidb.py
```

## References
- Endpoint: https://dgidb.org/api/graphql
- Docs: https://www.dgidb.org/api
