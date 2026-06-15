---
name: data-acquisition
description: "Use when: downloading/staging external data (Census, IPUMS, NCES, intel download scripts). Probe→stage→register. Then /dataset-register. NOT papers (/research)."
user-invocable: true
argument-hint: "[probe|acquire|catalog] <url-or-dataset-id>"
allowed-tools: [Read, Glob, Grep, Bash, Write, WebFetch]
effort: medium
---

# Data Acquisition

Empirical work in **research** and **intel** needs external datasets. This skill
codifies the shared probe→stage→register pattern.

## Repo routing

| Repo | Staging | Register | Repo-specific skill / docs |
|------|---------|----------|----------------------------|
| **research** | `sources/<topic>/data/external/stage3/<source>/<dataset>/` | `research/<topic>-dataset-register.md` or `*-dataset-cards.md` | `/dataset-register`, `infra/*/acquire/` |
| **intel** | `datasets/{name}/` (or `$VOLUME_ROOT/corpus/{name}` for >1GB) | `docs/DATA_INVENTORY.md` | `/dataset`, `docs/workflows/add_dataset.md`, `docs/tools_registry.json` |

**Intel first:** before writing `tools/download_*.py`, check `docs/TOOLS_REFERENCE.md`
and `docs/tools_registry.json` — 400+ downloaders may already exist.

**Web scraping / bot bypass:** read `~/Projects/skills/references/data-acquisition/SKILL.md`
(curl_cffi, firecrawl, chrome-cookies, fallback chains).

**Default staging root (research):** `sources/<topic>/data/external/stage3/<source>/<dataset>/`
**Alternate (large files):** `/Volumes/SSK1TB/corpus/<source>/<dataset>/` or intel `$VOLUME_ROOT/corpus/`

---

## Phase 1 — Probe before pull

Before any `curl`/`wget` of a file >10MB, answer four questions:

1. **Is it already local?** Check both:
   ```bash
   # Research topic-local stage
   ls sources/*/data/external/stage3/ 2>/dev/null | grep -i <dataset>
   # Intel datasets dir
   ls datasets/ 2>/dev/null | grep -i <dataset>
   # SSD corpus (research or intel volume root)
   ls /Volumes/SSK1TB/corpus/ 2>/dev/null | grep -i <source>
   ls "${VOLUME_ROOT:-$HOME/research-data}/corpus/" 2>/dev/null | grep -i <source>
   ```
2. **Is the URL live?** `curl -sS -I -L <url>` — check `HTTP/1.1 200`, `Content-Length`, `Last-Modified`.
3. **Is it the right size?** If `Content-Length` ≠ expected, the page may be an HTML landing, not the file.
4. **What's the codebook URL?** Download data + codebook in the same pass. Rule of thumb: every `.zip`/`.csv`/`.dta` needs a matching `.pdf` or `.txt` codebook.

### When the URL is dead: Wayback Machine

```bash
# Check if archived
curl -sS "http://archive.org/wayback/available?url=<url>&timestamp=20240101" | jq '.archived_snapshots.closest'
# If archived, fetch:
curl -sS -L -o file.pdf "https://web.archive.org/web/<timestamp>/<url>"
```

---

## Phase 2 — Stage

Staging convention: `sources/<topic>/data/external/stage3/<source>/<dataset>/`

Example for AHRQ MEPS HC-251:
```
sources/immigration-fiscal/data/external/stage3/ahrq/meps/
├── h251doc.pdf         # codebook
├── h251cb.pdf          # codebook (appendix)
├── h251dat.zip         # data
├── h251dta.zip         # data (Stata)
└── ACQUIRED.md         # one-line provenance per file
```

**ACQUIRED.md format** (one entry per file):
```
2026-04-18 | h251dat.zip | https://meps.ahrq.gov/.../h251dat.zip | 12.3M | sha256:abc...
```

---

## Phase 3 — Register

After staging, update the repo's dataset catalog:
- **research:** `research/<topic>-dataset-register.md` or `*-dataset-cards.md` — see `/dataset-register`
- **intel:** `docs/DATA_INVENTORY.md` + regenerate `tools/export_views_catalog.py` if DuckDB views added — see `/dataset`

See `/dataset-register` skill for research card format.

---

## Source-specific patterns

### Census (SIPP, ACS, QWI, decennial)

```bash
# Direct bulk file: www2.census.gov/programs-surveys/<program>/data/datasets/...
curl -sS -L -o pu2024_csv.zip \
  "https://www2.census.gov/programs-surveys/sipp/data/datasets/2024/pu2024_csv.zip"

# Census Data API (requires DATA_GOV_API_KEY from intel's .env)
# ACS 5-year state-level immigrant share:
curl -sS "https://api.census.gov/data/2022/acs/acs5?get=NAME,B05002_013E&for=state:*&key=${DATA_GOV_API_KEY}"
```

See `/census-data` skill for IPUMS + Census API patterns.

### AHRQ MEPS

```bash
# Each file has a predictable path:
BASE="https://meps.ahrq.gov/mepsweb/data_files/pufs"
for f in h251doc.pdf h251cb.pdf h251dat.zip h251dta.zip; do
  curl -sS -L -o "$f" "$BASE/$f"
done
```

### BLS (requires BLS_API_KEY)

```bash
# Registered API — 500 req/day
curl -sS -H "Content-Type: application/json" -X POST \
  "https://api.bls.gov/publicAPI/v2/timeseries/data/" \
  -d '{"seriesid":["LNS14000000"],"startyear":"2020","endyear":"2024","registrationkey":"'${BLS_API_KEY}'"}'
```

### FRED (requires FRED_API_KEY)

```bash
curl -sS "https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key=${FRED_API_KEY}&file_type=json"
```

### NCES DataLab

Not API-accessible. Requires browser session. See `research/iq-sex-differences-nces-datalab-acquisition.md`.

### PSID / Add Health

Registration-gated. See `research/iq-sex-differences-access-playbook.md` for the per-repo registration state.

### IPUMS (ACS, CPS, USA)

Extract-based, not bulk. See `/census-data` skill.

### YouTube transcripts

See `/youtube-transcript` skill.

---

## API keys

Research repo `.env` should mirror the relevant subset from `~/Projects/intel/.env.local`:

```
DATA_GOV_API_KEY=...   # Census API, data.gov datasets
BLS_API_KEY=...
FRED_API_KEY=...
COURTLISTENER_API_KEY=...
SAM_API_KEY=...        # SAM.gov federal contracts
TRADE_GOV_API_KEY=...
```

Symlink or copy — don't commit. `.env` is gitignored.

---

## When NOT to use

- Paper PDFs — use `mcp__research__fetch_paper` (Sci-Hub + OpenAlex).
- Academic search — use exa / brave-search / research-mcp.
- General web scraping — use firecrawl or the Chrome MCP (`mcp__claude-in-chrome__*`).
- Google Sheets / Drive — use `/google-workspace`.

## Evidence

- 18+ ad-hoc acquisition scripts across `sources/*/scripts/` — same probe/stage/register pattern reinvented.
- `immigration-public-data-acquisition-2026-04-11.md`, `iq-sex-differences-access-playbook.md` — manual playbooks.
- SSD corpus (`/Volumes/SSK1TB/corpus/`) not consistently checked before re-downloads.
