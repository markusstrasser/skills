---
name: papers
description: "Canonical local store for PDFs + parses + citation graph. 'check papers store', 'cite something', 'find contradicting citations', 'has any repo already seen this DOI'."
user-invocable: true
argument-hint: '[doi | pmid | paper_id | "stats"]'
allowed-tools: [Bash, Read]
effort: low
---

# papers — Canonical Local Paper Store

A single content-addressed store at `~/Projects/papers/` shared across
genomics, phenome, research-mcp, agent-infra. Holds PDFs + marker-parsed
markdown + scite/openalex citation context + a DuckDB citation graph.
Before fetching, parsing, or citing — **check here first**.

The user manages this on their own machine; no auth, no remote, no
multi-tenant. Source of truth at
`~/Projects/agent-infra/scripts/papers/`. Schema at
`~/Projects/papers/SCHEMA.md`. Plan at
`~/Projects/agent-infra/.claude/plans/2026-05-11-shared-papers-store.md`.

## When to use

- **Before fetching a paper by DOI/PMID** — `papers stats` + paper_id derivation tells you if it's already on disk
- **When citing something to support a claim** — `papers cited-by` returns the actual supporting/contrasting snippets with paper IDs and CiTO stance, not just counts
- **When checking for contradictions** — `papers contradictions <id>` surfaces incoming citances flagged `cito:disagreesWith`, including any retracted-citing-paper signals
- **Cross-repo discovery** — INDEX.json on each paper records which repos (genomics/phenome/research-mcp/agent-infra) reference it, so "has any repo already done work against this source?" is a filesystem grep

## CLI surface

```bash
uvx papers stats                           # paper count, total size, graph node/edge counts
uvx papers show <paper_id>                 # metadata + parsed paths + used_by
uvx papers ingest --pdf <path> --doi <doi>  # ingest; runs marker chunked at 3 pages on MPS
uvx papers ingest --revise --pdf <new> --paper-id <id>  # archive old, ingest new revision

# Graph queries (after maintain --rebuild-graph)
uvx papers cites <paper_id>                # outbound edges + snippets + stance
uvx papers cited-by <paper_id>             # inbound edges
uvx papers cited-by <paper_id> --stance contrasting
uvx papers contradictions <paper_id>       # cito:disagreesWith + retraction-flagged citers
uvx papers ego <paper_id> --depth 2        # N-hop neighbourhood
uvx papers path <a> <b>                    # shortest path
uvx papers similar <paper_id> --via co-citation | --via biblio-coupling

# Collections + tables
uvx papers collection {list, new, add, diff}
uvx papers table --cols schema.yaml --paper-ids ...

# Maintenance (operator-run, no cron)
uvx papers maintain --verify               # parsed.sha256 + pdf_sha256 drift detection
uvx papers maintain --rebuild-indexes      # rebuild INDEX.json.used_by across repos
uvx papers maintain --rebuild-citances [--paper-id <id> | --all]
uvx papers maintain --rebuild-graph        # rebuild graph.duckdb from per-paper JSONL
uvx papers maintain --gc --after-rebuild --dry-run
```

## Identity rule

`paper_id` is **stable for the life of the paper, including reissues**:

| Source | `paper_id` |
|---|---|
| has DOI | `doi_<slugified_doi>` (e.g. `doi_10_1097_FPC_0000000000000456`) |
| has PMID, no DOI | `pmid_<pmid>` |
| neither | `sha_<sha256[:16]>` |

DOI collision check fails closed at ingest. Reissues are versions
inside the same `paper_id` directory — old PDF renamed to
`paper.<old_sha_prefix>.pdf`, old parsed/ becomes `parsed.<old_parser_id>/`.

## Per-paper layout

```
~/Projects/papers/<paper_id>/
  paper.pdf                       # current canonical PDF
  paper.<sha_prefix>.pdf          # prior revisions, archived
  metadata.json                   # SINGLE authority — doi, pmid, title, sha, parser, revisions, fabio_class, wikidata_qid, openalex_id, contributions
  parsed/                         # immutable per parser_id
    paper.md
    paper_meta.json               # block bboxes — page anchors
    _page_N_Figure_M.jpeg         # figure crops
    parsed.sha256
    parser.json                   # {marker, surya, llm, config_md5, ts}
  citation_context/
    scite_response.json
    openalex_response.json
    pubmed_response.json
    crossref_response.json
    latest_event.json
  citances_in.jsonl               # DERIVED — papers citing THIS paper (CiTO stance + scite class + snippet + confidence)
  citances_out.jsonl              # DERIVED — papers THIS paper cites
  references_resolved.json        # DERIVED — reference-string → (doi, pmid) cache
  annotations.jsonl               # APPEND-ONLY — paper-level observations from agents/operator
  INDEX.json                      # DERIVED cache — used_by: [{repo, source_id, claim_ids}, ...]
```

## Common workflows

**Before citing a paper to support a claim:**
```bash
papers show doi_10_1056_NEJMoa0809171 --depth full  # see retraction status + contributions
papers cited-by doi_10_1056_NEJMoa0809171 --stance contrasting  # is there counter-evidence?
papers contradictions doi_10_1056_NEJMoa0809171  # flagged disagreements with provenance
```

**When research-mcp fetches a paper (already integrated):**
```python
from research_mcp.papers import download_paper, extract_text
paper_id = download_paper("10.1101/2026.04.10.26350624")  # cache-hit instantaneous; else download+ingest
text = extract_text(paper_id)  # prefers parsed/paper.md → Gemini → PyMuPDF fallback
```

**Recording a personal observation about a paper:**
Append to `~/Projects/papers/<paper_id>/annotations.jsonl` (event-sourced; never edit). Use `kind: "contribution"` for ORKG-style structured key findings, `kind: "contradiction_flag"` for noticed disagreements, `kind: "note"` for general observations. `target.kind` ∈ `paper | passage | figure | citance`.

## What this is NOT

- Not a publishing target — `papers export --to-nanopub` is a future option, not active
- Not a remote service — local store, single user
- Not a backup — `papers sync --from manifest.json` is best-effort upstream bootstrap; durable recovery is the operator's filesystem snapshot (Time Machine)
- Not a Wikidata mirror — uses `wikidata_qid` as a cross-link, doesn't try to replicate
- Not a SPARQL endpoint — DuckDB + CLI

## Related skills

- `research` — discovers papers via web search; once you have a DOI, ingest into the store
- `bio-verify` — verifies hardcoded bio constants; the store can hold the supporting evidence
- `life-science-research` — multi-lane router for biomedical sources; papers ingested here serve as the durable evidence cache

## Vetoes

- Do NOT propose Neo4j or other native graph DB — DuckDB validated by production scholarly graphs (OpenAlex 2.1B edges, S2AG 2.5B, OpenCitations RDF all use columnar/relational)
- Do NOT propose per-repo paper storage — the canonical store dedupes across all four repos
- Do NOT propose Nanopublications as the primary format — TriG + RSA signing is wrong for a personal reading loop
- Do NOT propose SPECTER2 embeddings as Phase 1 — defer; citation graph value comes first

## Provenance

- Phase 1 implementation: agent-infra `b365da5` (merge of `c29dfa1..85aec1d`)
- Phase 3 research-mcp integration: research-mcp `8d28fb1`, `e015a1f`
- Plan + critique: `~/Projects/agent-infra/.claude/plans/2026-05-11-shared-papers-store.md`
- Research backing: `~/Projects/agent-infra/research/{pdf-to-markdown-tooling, scientific-citation-graph-patterns, paperqa-evidence-model, ai-literature-tools-schemas, scientific-kg-schema-standards}-2026-05.md`
