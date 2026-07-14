# Marker PDF→Markdown on Modal — Default Over Local

For any PDF → markdown extraction with `marker-pdf` (especially scanned books,
multi-page extractions, or anything with figures/equations), **default to
Modal-hosted Marker on T4, not local marker_single**.

## Why

- **Local Marker on the Mac is broken/slow.** MPS backend has surya layout
  bugs (`index 8192 is out of bounds` crashes at ~page 6 on large docs,
  surya issues #993 / #967 / #960). CPU fallback works but is ~20× slower since
  marker-pdf v1.9.0 — a 38-page Part-I extract on `Vision (Marr)` took 15+ min
  CPU; the T4 path does the same job in ~1 min cold.
- **Pre-baked weights.** `corpus_marker_modal.py` bakes surya/marker weights
  into the image, so cold-start is ~30 s (vs ~3 min cold-downloading them).
- **Cost.** ~$0.005-0.013 per 41-page PDF cold, ~$0.0025 warm. Idle = $0
  (`min_containers=0`).
- **Consistent model.** Defaults to `gemini-3-flash-preview` — matches the
  global preference (see `feedback_gemini_model_choice.md`).

## How to use

The script lives at `~/Projects/agent-infra/scripts/corpus_marker_modal.py` and
is exposed through the `corpus` CLI (uv-tool installed globally):

```bash
# Single PDF — marker-modal is the DEFAULT for papers/preprints (2026-05-31),
# so --parser is optional for those source types:
corpus ingest --pdf path/to/doc.pdf
corpus ingest --pdf path/to/doc.pdf --parser marker-modal   # explicit, same result

# Batch
corpus ingest-batch --dir path/to/pdfs/

# Offline / no network — opt OUT to the local parser:
corpus ingest --pdf path/to/doc.pdf --parser mineru
```

`DEFAULT_PARSER["paper"|"preprint"] = "marker-modal"` lives in
`research-mcp/src/research_mcp/corpus/extract/__init__.py`.
Existing parses are immutable/content-addressed, so this only affects NEW ingests.

If `corpus` isn't appropriate (e.g., you need raw markdown + image crops
returned in-band, not into the corpus index), invoke the Modal function
directly:

```python
import modal
fn = modal.Function.from_name("corpus-marker", "extract_pdf")
result = fn.remote(pdf_bytes, parser_config={"page_range": "27-64"})
# result["ok"], result["markdown"], result["images_zip_b64"], ...
```

`parser_config` is passed straight to marker's config_json — supports
`page_range`, `force_ocr`, `redo_inline_math`, `extract_images`, etc.

## Deploy check

If `modal app list | grep corpus-marker` is empty:

```bash
modal secret create gemini-api-key GEMINI_API_KEY=$GEMINI_API_KEY  # once
uv run modal deploy ~/Projects/agent-infra/scripts/corpus_marker_modal.py
```

## When local marker is still right

- Single page or 2-3 page probe where Modal cold-start (~30 s) dwarfs the work.
- No network / offline.
- Debugging marker config — local iteration is faster than redeploying.

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
