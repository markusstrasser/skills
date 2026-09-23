# Marker PDF→Markdown on Modal — Default Over Local

For any PDF → markdown extraction with `marker-pdf` (especially scanned books,
multi-page extractions, or anything with figures/equations), **default to
Modal-hosted Marker 2 on L4, not local marker_single**.

## Why

- **Local path is text-layer only by design.** Marker 2 needs a VLM inference
  server (vLLM on NVIDIA / llama.cpp on Mac). We do **not** run a local VLM —
  `--parser marker` defaults to `fast + --disable_ocr` (pdftext only). For
  figures/equations/OCR fidelity, use Modal.
- **Marker 2 on Modal.** `corpus_marker_modal.py` runs marker-pdf≥2.0 with
  `--mode balanced`, starts an in-container vLLM serving `datalab-to/surya-ocr-2`
  (Docker spawn is impossible on Modal), and applies Gemini cleanup
  (`--use_llm`, `gemini-3.8-flash`, `thinking_budget=0`).
- **Pre-baked weights.** Image bake downloads surya-ocr-2 + layout2 so cold
  containers skip the multi-GB HF fetch; first call still pays vLLM load.
- **Cost (measured, 41-page PDF, L4 ≈ $0.80/hr).** Cold 419 s ≈ $0.09, most of
  it vLLM load; warm 84.5 s ≈ $0.02. Idle = $0 (`min_containers=0`).
  `scaledown_window=180` keeps vLLM warm, so batch PDFs back to back.

## How to use

The script lives at `~/Projects/research-mcp/scripts/corpus_marker_modal.py`
and is exposed through the `corpus` CLI / research-mcp ingest:

```bash
# Single PDF — marker-modal is the DEFAULT for papers/preprints,
# so --parser is optional for those source types:
corpus ingest --pdf path/to/doc.pdf
corpus ingest --pdf path/to/doc.pdf --parser marker-modal   # explicit, same result

# Batch
corpus ingest-batch --dir path/to/pdfs/

# Offline / no network — opt OUT:
corpus ingest --pdf path/to/doc.pdf --parser mineru          # structured local
corpus ingest --pdf path/to/doc.pdf --parser marker          # Marker 2 text-layer only
```

`DEFAULT_PARSER["paper"|"preprint"] = "marker-modal"` lives in
`research-mcp/src/research_mcp/corpus/extract/__init__.py`.
Existing parses are immutable/content-addressed, so this only affects NEW ingests
(parser_id now includes `+balanced+…`).

If `corpus` isn't appropriate (e.g., you need raw markdown + image crops
returned in-band, not into the corpus index), invoke the Modal function
directly:

```python
import modal
fn = modal.Function.from_name("corpus-marker", "extract_pdf")
result = fn.remote(pdf_bytes, parser_config={"page_range": "27-64"})
# result["ok"], result["markdown"], result["parsed_zip_b64"], ...
```

`parser_config` keys: `page_range`, `force_ocr`, `redo_inline_math`,
`extract_images`, `use_llm`, `gemini_model_name`, `mode` (default `balanced`).

## Deploy check

If `modal app list | grep corpus-marker` is empty / stale on 1.10:

```bash
modal secret create gemini-api-key GEMINI_API_KEY=$GEMINI_API_KEY  # once
uv run --with modal modal deploy ~/Projects/research-mcp/scripts/corpus_marker_modal.py
# smoke:
uv run --with modal modal run ~/Projects/research-mcp/scripts/corpus_marker_modal.py --pdf ~/Projects/corpus/<id>/paper.pdf
```

## When local marker is still right

- Offline text-layer probe (`--parser marker` → fast + disable_ocr).
- Debugging config without redeploying Modal.

Otherwise: **default to Modal**.

## Evidence

2026-05-16 — Marr Vision (Marr 1982, 429 pp) Part-I prototype build. First
attempt with local MPS crashed at page 6 of 38 (`index 8192 is out of bounds`).
CPU fallback ran 15+ min before completion (would've been ~1 min on T4). User
called out the missed Modal option mid-session.

> Provenance: lifted verbatim from the always-loaded global rule
> `~/.claude/rules/marker-modal-default.md` on 2026-06-12 (Tier A4 rule
> path-scoping, plan `2026-06-12-master-harness-improvement.md`); the global
> rule is now a 3-line stub.

2026-07-20 — marker-pdf 2.0.0 released: `--mode balanced|fast`, selective OCR,
a VLM server for surya-ocr-2. The Modal image moved T4→L4 with in-process vLLM
(no nested Docker).

2026-09-23 — An unpinned redeploy pulled 2.0.0 into the Marker 1.x app and
broke it (no rollback on this plan); a 1.10.2 pin restored it as v3. The
Marker 2 migration then deployed as v4 (research-mcp 42d6db9, c1446df):
ephemeral run 110,021 chars vs a 112,653 baseline, deployed smokes cold 419 s
and warm 84.5 s. Marker 1.x on T4 had been ~1 min and ~$0.01 cold.
