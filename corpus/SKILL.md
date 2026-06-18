---
name: corpus
description: "Use when: corpus cite/attest, 'has repo seen this DOI', contradicting citations. Local source store — NOT web literature (/research)."
user-invocable: true
argument-hint: '[doi | pmid | paper_id | "stats"]'
allowed-tools: [Bash, Read]
effort: low
---

# corpus — Canonical Local Source Store

A single content-addressed store at `~/Projects/corpus/` shared across
genomics, phenome, research-mcp, agent-infra. Holds source bytes (PDFs, HTML, etc.)
+ parsed markdown + scite/openalex citation context + a DuckDB graph index
+ append-only annotations.
Before fetching, parsing, or citing — **check here first**.

The user manages this on their own machine; no auth, no remote, no
multi-tenant. Source of truth at
`~/Projects/agent-infra/scripts/corpus/`. Schema at
`~/Projects/corpus/SCHEMA.md`.

## When to use

- **Before fetching a source by DOI/PMID** — `corpus stats` + paper_id derivation tells you if it's already on disk
- **When citing something to support a claim** — `corpus cited-by` returns the actual supporting/contrasting snippets with paper IDs and CiTO stance, not just counts
- **When checking for contradictions** — `corpus contradictions <id>` surfaces incoming citances flagged `cito:disagreesWith`, including any retracted-citing-paper signals
- **Cross-repo discovery** — INDEX.json on each source records which repos (genomics/phenome/research-mcp/agent-infra) reference it, so "has any repo already done work against this source?" is a filesystem grep

## CLI surface

Ships in `corpus-core`, installed as a uv tool → **`corpus` on PATH**. Do **NOT** use `uvx corpus` — that fetches an unrelated PyPI squat (`corpus` 0.4.2, no executable), not this tool. Every command needs `--corpus-root <store>` (`required=True`, no default). Canonical store: `~/Projects/corpus`. Set once so the commands below work as written:
```bash
alias corpus='corpus --corpus-root ~/Projects/corpus'
```

```bash
corpus stats                            # source count, total size, graph node/edge counts
corpus show <paper_id>                  # metadata + parsed paths + used_by
corpus ingest --pdf <path> --doi <doi>  # ingest a paper
corpus ingest --revise --pdf <new> --paper-id <id>  # archive old, ingest new revision

# Graph queries (after maintain --rebuild-graph)
corpus cites <paper_id>                # outbound edges + snippets + stance
corpus cited-by <paper_id>             # inbound edges
corpus cited-by <paper_id> --stance contrasting
corpus contradictions <paper_id>       # cito:disagreesWith + retraction-flagged citers
corpus ego <paper_id> --depth 2        # N-hop neighbourhood
corpus path <a> <b>                    # shortest path
corpus similar <paper_id> --via co-citation | --via biblio-coupling

# Collections + tables
corpus collection {list, new, add, diff}
corpus table --cols schema.yaml --paper-ids ...

# Maintenance (operator-run, no cron)
corpus maintain --verify               # parsed.sha256 + pdf_sha256 drift detection
corpus maintain --rebuild-indexes      # rebuild INDEX.json.used_by across repos
corpus maintain --rebuild-citances [--paper-id <id> | --all]
corpus maintain --rebuild-graph        # rebuild graph.duckdb from per-source JSONL
corpus maintain --gc --after-rebuild --dry-run
```

## Parser selection (`--parser`)

`corpus ingest` picks a default by source type; override with `--parser <name>`.
Defaults: **papers/preprints → `mineru`**, non-paper PDFs → `pymupdf4llm`,
web/blog/news → `trafilatura`. Opt-in parsers must be passed explicitly.

| Parser | License | Output | Reach for it when |
|---|---|---|---|
| `mineru` *(default: papers)* | Apache-2.0+ | structured md (headings, tables, equations) | Default for papers/preprints. Structure is the deliverable. |
| `pymupdf4llm` *(default: other PDFs)* | AGPL-3.0 | markdown (headings + tables) | Local-only structured extraction of born-digital docs. NOT server-side (AGPL). |
| `trafilatura` *(default: web)* | Apache-2.0 | markdown | HTML/blog/news bytes. |
| `marker` / `marker-modal` *(opt-in)* | GPL-3.0 | structured md + figure crops | Scanned / figure-heavy / equation-dense papers. `marker-modal` runs on Modal T4 (see global `marker-modal-default.md`); local `marker` has Mac MPS bugs. |
| `liteparse` *(opt-in)* | Apache-2.0 | **flat text only** | Fast bulk text recall, **office docs** (.docx/.pptx/.xlsx), when an **Apache license** is required, or as a **scan-vs-digital preflight**. |
| `gemini-flash-lite` *(opt-in)* | cloud LLM | markdown | Last-resort fallback for PDFs every local parser fails. |

**Do NOT use `liteparse` for papers you need *structured*.** It emits a flat
character stream — zero headings, zero tables, no reading order. Bake-off on 6
corpus papers (2026-05-28): liteparse is ~100–300× faster (0.1–0.5s vs 12–42s)
and recovers ~30–45% more raw characters, but `pymupdf4llm`/`mineru` recover
9–32 headings and up to 108 table rows per paper that liteparse drops entirely.
More characters ≠ better — liteparse's surplus is partly running
headers/page-numbers, not structure. For papers → markdown → chunking/claims,
structure wins; liteparse is for the niches above, not paper bodies.

**Preflight pattern** (route scanned PDFs to the expensive path cheaply):
liteparse returns `extras.has_text_layer` — `False` means no extractable text
(scanned/image PDF) ⇒ send it to `mineru`/`marker-modal`, don't waste a flat-text
pass. Install: `pip install liteparse` (corpus extra `liteparse`).

## Identity rule

`source_id` (paper-typed: `paper_id`) is **stable for the life of the source, including reissues**:

| Source | `source_id` |
|---|---|
| has DOI | `doi_<slugified_doi>` (e.g. `doi_10_1097_fpc_0000000000000456`) |
| has PMID, no DOI | `pmid_<pmid>` |
| neither | `sha_<sha256[:16]>` |

DOI collision check fails closed at ingest. Reissues are versions
inside the same `source_id` directory — old PDF renamed to
`paper.<old_sha_prefix>.pdf`, old parsed/ becomes `parsed.<old_parser_id>/`.

## Per-source layout

```
~/Projects/corpus/<source_id>/
  paper.pdf                       # current canonical PDF (paper-typed sources)
  paper.<sha_prefix>.pdf          # prior revisions, archived
  metadata.json                   # SINGLE authority — doi, pmid, title, sha, parser, revisions, fabio_class, wikidata_qid, openalex_id, contributions
  parsed.<parser_id>/             # immutable per parser_id (Phase 1.5)
    page.md
    page_meta.json                # block bboxes — page anchors
    _page_N_Figure_M.jpeg         # figure crops
    parsed.sha256
    parser.json                   # {parser_id, version, llm, config_md5, ts}
  citation_context/
    scite_response.json
    openalex_response.json
    pubmed_response.json
    crossref_response.json
    latest_event.json
  citances_in.jsonl               # DERIVED — sources citing THIS source (CiTO stance + scite class + snippet + confidence)
  citances_out.jsonl              # DERIVED — sources THIS source cites
  references_resolved.json        # DERIVED — reference-string → (doi, pmid) cache
  annotations.jsonl               # APPEND-ONLY — per-source observations from agents/operator (Phase 1)
  INDEX.json                      # DERIVED cache — used_by: [{repo, source_id, claim_ids}, ...]
```

## Common workflows

**Before citing a paper to support a claim:**
```bash
corpus show doi_10_1056_nejmoa0809171 --depth full  # see retraction status + contributions
corpus cited-by doi_10_1056_nejmoa0809171 --stance contrasting  # is there counter-evidence?
corpus contradictions doi_10_1056_nejmoa0809171  # flagged disagreements with provenance
```

**When research-mcp fetches a paper (already integrated):**
```python
from research_mcp.papers import download_paper, extract_text
paper_id = download_paper("10.1101/2026.04.10.26350624")  # cache-hit instantaneous; else download+ingest
text = extract_text(paper_id)  # prefers parsed/page.md → Gemini → PyMuPDF fallback
```

**Recording a personal observation about a source:**
Use the `corpus annotate` CLI (`corpus annotate --source-id <id> --repo <r>
--actor-type cli --actor-id <urn> --scope <s> ...`). It routes through
`corpus_core.annotate` — the SOLE writer — and appends to
`~/Projects/corpus/<source_id>/annotations.jsonl` (event-sourced; never edit
by hand). Use `kind: "contribution"` for ORKG-style structured key findings,
`kind: "contradiction_flag"` for noticed disagreements,
`kind: "note"` for general observations.

There is no `corpus_attest` MCP tool: substrate v2 retired the agent-facing
write path. Substantive repo assertions (verdicts/certs/contradictions) are
attested automatically by each repo's mutation gateway via a transactional
outbox; standalone observations use the CLI above. See
`agent-infra/decisions/2026-05-26-cross-attestation-substrate-v2.md`.

## What this is NOT

- Not a publishing target — RO-Crate / BagIt export is a Phase 8 option
- Not a remote service — local store, single user
- Not a backup — `corpus sync --from manifest.json` is best-effort upstream bootstrap; durable recovery is the operator's filesystem snapshot (Time Machine)
- Not a Wikidata mirror — uses `wikidata_qid` as a cross-link, doesn't try to replicate
- Not a SPARQL endpoint — DuckDB + CLI

## Related skills

- `research` — discovers papers via web search; once you have a DOI, ingest into the store
- `bio-verify` — verifies hardcoded bio constants; the store can hold the supporting evidence

## Vetoes

- Do NOT propose Neo4j or other native graph DB — DuckDB validated by production scholarly graphs (OpenAlex 2.1B edges, S2AG 2.5B, OpenCitations RDF all use columnar/relational)
- Do NOT propose per-repo source storage — the canonical store dedupes across all four repos
- Do NOT propose Nanopublications as the primary format — TriG + RSA signing is wrong for a personal reading loop
- Do NOT propose SPECTER2 embeddings as Phase 1 — defer; citation graph value comes first
