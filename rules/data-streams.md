# Data Stream Ownership Model

Every project has three data streams with distinct protection levels.

## Stream 1: Human-Authored (append-only)

Content created by the human — irreplaceable institutional knowledge. Each version contains
unique analytical content, exploration paths, and intermediate reasoning that is lost if deleted.

**Protection:** `pretool-append-only-guard.sh` blocks content shrinkage.
**Rule:** Mark stale, never delete. Corrections get new entries (conviction journal pattern).

## Stream 2: External/Raw (read-only)

Data from APIs, downloads, databases, instruments. Gitignored, reproducible by re-downloading.
Agents must not modify raw data — derive outputs to Stream 3.

**Protection:** `pretool-data-guard.sh` blocks Write/Edit to configured paths.

## Stream 3: Agent-Derived (rederivable)

Analysis, reports, scripts — tracked in git, can be regenerated from Stream 1 + Stream 2.
No special protection needed.

## Per-Project Mapping

| Stream | intel | genomics | selve | meta |
|--------|-------|----------|-------|------|
| 1 (append-only) | conviction journal | manual curation | self-reports, docs/entities | improvement-log, decisions |
| 2 (read-only) | datasets/, *.parquet | data/, databases/, VCF/BAM | data/ | (none) |
| 3 (rederivable) | analysis/ | docs/research/, scripts/ | docs/derived/ | research/, scripts/ |

Each project configures stream protections via env vars in `.claude/settings.json`:
- `PROTECTED_PATHS` for Stream 2 (pretool-data-guard.sh)
- `APPENDONLY_PATHS` for Stream 1 (pretool-append-only-guard.sh)
