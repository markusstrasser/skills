---
name: census-data
description: "Census Data API + IPUMS extract patterns for ACS, CPS, SIPP, QWI, decennial, and USA microdata. Use when: pulling state/county aggregates, building a microdata extract, computing immigrant shares, estimating earnings by group, or replicating a Card/Borjas-style panel. Covers: Census Data API (variable lookup, geography codes, summary tables), IPUMS extract API (USA, CPS, International), QWI state panel, and common variable codes (B05002 nativity, B19013 income, etc.)."
user-invocable: true
argument-hint: "[acs|cps|qwi|sipp|ipums] <geography-or-extract>"
allowed-tools: [Read, Glob, Grep, Bash, Write, WebFetch]
effort: medium
---

# Census Data

Patterns for Census Data API and IPUMS extracts. Complements `/data-acquisition`
(general pattern) with source-specific variable codes and extract mechanics.

## API keys

```bash
source ~/Projects/research/.env   # DATA_GOV_API_KEY, IPUMS_API_KEY (if set)
```

---

## Census Data API

Base: `https://api.census.gov/data/<year>/<dataset>?get=<vars>&for=<geo>&key=...`

### Common datasets

| Dataset ID | Meaning | Years |
|---|---|---|
| `acs/acs5` | ACS 5-year (most stable for small geos) | 2009–latest |
| `acs/acs1` | ACS 1-year (places ≥65K) | 2005–latest |
| `dec/sf1` | Decennial Summary File 1 | 2000, 2010 |
| `dec/pl` | Decennial Redistricting | 2020 |
| `timeseries/qwi/se` | QWI state × industry × demographic | 2000q1–present |
| `timeseries/cps` | Current Population Survey | Monthly |

### High-value variable codes

**Nativity (B05002):**
- `B05002_001E` — Total
- `B05002_013E` — Foreign-born
- `B05002_014E` — Naturalized citizen
- `B05002_021E` — Not a U.S. citizen

**Income:**
- `B19013_001E` — Median household income
- `B19301_001E` — Per capita income

**Education (B15003):**
- `B15003_022E` — Bachelor's
- `B15003_025E` — Doctorate

### Example: state-level immigrant share

```bash
curl -sS "https://api.census.gov/data/2022/acs/acs5?get=NAME,B05002_001E,B05002_013E&for=state:*&key=${DATA_GOV_API_KEY}" | jq
```

### Variable discovery

```bash
# Search for variables containing "nativity"
curl -sS "https://api.census.gov/data/2022/acs/acs5/variables.json" | \
  jq '.variables | to_entries[] | select(.value.label | test("nativity"; "i")) | {id: .key, label: .value.label}'
```

---

## QWI (Quarterly Workforce Indicators)

State × industry × demographic panel from LEHD. Used for Card-vs-Borjas E-Verify analysis.

```bash
# All-workers employment by state, 2003q1–2023q4
for year in $(seq 2003 2023); do
  curl -sS "https://api.census.gov/data/timeseries/qwi/se?get=Emp,EarnBeg&for=state:*&time=from+${year}-Q1+to+${year}-Q4&key=${DATA_GOV_API_KEY}" \
    > "qwi_${year}.json"
done
```

Existing implementation: `sources/immigration-causal/scripts/pull_qwi_state_panel.py`.

---

## IPUMS

Extract-based — build a request, submit, poll, download. API key from https://account.ipums.org/api_keys.

**Workflow:**
1. Install: `uv pip install ipumspy` (or in pyproject)
2. Create extract spec (YAML or dict): specify samples, variables, data format
3. Submit → returns `extract_id`
4. Poll status every 30s until `completed`
5. Download `.dat.gz` + `.xml` codebook

**Minimal Python:**
```python
from ipumspy import IpumsApiClient, UsaExtract
client = IpumsApiClient(os.environ["IPUMS_API_KEY"])
extract = UsaExtract(
    samples=["us2022a", "us2021a"],
    variables=["AGE", "SEX", "NATIVITY", "YRIMMIG", "INCTOT"],
)
client.submit_extract(extract)
client.wait_for_extract(extract)
client.download_extract(extract, download_dir="sources/<topic>/data/external/ipums/")
```

**Collections:** `UsaExtract` (ACS + decennial), `CpsExtract` (CPS monthly), `IpumsiExtract` (International).

---

## SIPP (Survey of Income and Program Participation)

Bulk CSV + documentation, no API:
```bash
BASE="https://www2.census.gov/programs-surveys/sipp"
curl -sS -L -o pu2024_csv.zip "${BASE}/data/datasets/2024/pu2024_csv.zip"
curl -sS -L -o 2024_SIPP_Users_Guide.pdf "${BASE}/tech-documentation/methodology/2024_SIPP_Users_Guide.pdf"
```

---

## Pitfalls

- **Margin of error (MOE):** ACS returns point estimates AND `_M` (MOE) columns. For significance, use `_M` not just `_E`.
- **Suppression:** `-555555555` = value suppressed for privacy. Filter before aggregating.
- **Year-over-year variable drift:** Some ACS variable codes change definitions. Check `variables.json` for the actual year you're pulling.
- **QWI geography:** `state:*` works; `county:*` needs `in=state:XX`.
- **IPUMS sample codes:** `us2022a` (a = ACS 1-year); `us2022b` = 5-year. Use `a` unless you have a reason.

## Evidence

- `sources/immigration-causal/scripts/pull_acs_state_immigrant_share.py`
- `sources/immigration-causal/scripts/pull_qwi_state_panel.py`
- `sources/immigration-causal/scripts/merge_saiz_rent_immigrant.py`
- Recurring commit topic: `[research] Saiz × ACS rent merge`, `[research] E-Verify TWFE on QWI`
