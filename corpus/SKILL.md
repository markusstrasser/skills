---
name: corpus
description: "Use when: local paper lookup, 'has the corpus seen this DOI/PMID', cached full text, or canonical paper ingest. Local source store — NOT web literature (/research)."
user-invocable: true
argument-hint: '[doi | pmid | source_id | "stats"]'
allowed-tools: [Bash, Read]
effort: low
---

# corpus — canonical local paper store

The content-addressed paper store lives at `~/Projects/corpus/`. It holds source
bytes, immutable parser-addressed text, metadata, and parse-health state. Check it
before fetching or parsing a paper again.

The implementation and CLI belong to
`~/Projects/research-mcp/src/research_mcp/corpus/`. Substrate is dormant and is
not a runtime dependency.

## CLI

`research-mcp` is installed as an editable uv tool and exposes `corpus` on
`PATH`. Do not use `uvx corpus`; that name belongs to an unrelated PyPI
package. The root is always explicit:

```bash
corpus --corpus-root ~/Projects/corpus stats
corpus --corpus-root ~/Projects/corpus status
corpus --corpus-root ~/Projects/corpus lookup --doi 10.1000/example
corpus --corpus-root ~/Projects/corpus lookup --pmid 12345678
corpus --corpus-root ~/Projects/corpus show doi_10_1000_example
```

`lookup` is the cheap presence probe. `show` returns metadata and the active
parsed path. Read `parsed.<parser_id>/page.md` from that returned path.

## Ingest

```bash
corpus --corpus-root ~/Projects/corpus ingest --pdf paper.pdf --doi 10.1000/example
corpus --corpus-root ~/Projects/corpus ingest --url "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/" --pmid 12345678
corpus --corpus-root ~/Projects/corpus ingest --reparse --paper-id doi_10_1000_example --parser marker-modal
corpus --corpus-root ~/Projects/corpus ingest-batch --dir papers/ --parser marker-modal --max-parallel 5
```

For papers and preprints, `marker-modal` is the default: GPU Marker plus Gemini
cleanup. Use `pymupdf4llm` for a cheap local text-first parse, `trafilatura`
for HTML, or `mineru` only when layout recovery justifies it. Existing parses
are immutable and parser-addressed; reparse adds a new parse and repoints the
active one.

Identity priority is DOI, then PMID, then content hash. Never invent identifiers
or rename a source directory by hand.

## Research MCP

The same owner exposes paper lookup/fetch/read tools through research-mcp. Use
those when an MCP result is more convenient; use the CLI for filesystem-oriented
inspection and explicit ingest. Both paths write the same `~/Projects/corpus`
store.

## Boundaries

- Corpus annotations, cross-repo attestation, outboxes, claim relations, graph
  maintenance, and sync jobs were retired on 2026-07-14.
- The corpus is a local paper cache, not a verdict store, remote service, or
  backup system.
- Never edit source bytes, metadata, or parsed outputs in place. Ingest a
  revision or reparse through the CLI.
- Web discovery belongs to `/research`; this skill starts once a DOI, PMID,
  source ID, URL, or local source file is known.

## Related skills

- `research` — discover papers, then promote useful sources into this store.
- `bio-verify` — verify biological constants against authoritative databases;
  corpus can retain the supporting paper.
