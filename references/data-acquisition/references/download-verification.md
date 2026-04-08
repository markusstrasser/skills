<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Download Verification & Post-Download QA

## Download Verification

Always verify downloads contain what you expect:

```bash
# Check file type
file downloaded.zip                      # should say "Zip archive data"

# Check zip contents for actual data (not just docs)
unzip -l downloaded.zip | grep -iE '\.(sav|dta|dat|csv|tsv|parquet|sas7bdat|xpt) '

# Check for HTML trap (got a login page instead of data)
head -5 downloaded.csv                   # should NOT start with <!DOCTYPE
python3 -c "open('f.zip','rb').read(4)" # should be PK\x03\x04 for zip

# Check file size is reasonable
ls -lh downloaded.zip                    # 70 MB zip is real; 21 KB is codebook-only
```

## Resumable Downloads

For large files (>100 MB), use resume-capable downloads:

```python
import os
from curl_cffi import requests

def download_resumable(url, dest):
    headers = {}
    mode = "wb"
    if os.path.exists(dest):
        size = os.path.getsize(dest)
        headers["Range"] = f"bytes={size}-"
        mode = "ab"

    resp = requests.get(url, impersonate="chrome", headers=headers, stream=True)
    if resp.status_code == 416:  # Range not satisfiable = already complete
        return

    with open(dest, mode) as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)
```

## Post-Download QA — Data Profiling

After every download, profile the dataset before wiring it into anything. Don't skip this — HTML traps, truncated files, and wrong schemas are common.

### Quick Profile Sequence

```bash
# 1. Type and size
file downloaded.csv && wc -c downloaded.csv && wc -l downloaded.csv

# 2. Schema (CSV/TSV)
head -1 downloaded.csv | tr ',' '\n' | cat -n    # column names + count

# 3. Sample rows (check for actual data, not headers repeated)
head -5 downloaded.csv

# 4. Nulls/empties (sample-based)
awk -F',' '{for(i=1;i<=NF;i++) if($i=="") c[i]++} END{for(i in c) print "col "i": "c[i]" empty"}' downloaded.csv
```

### Format-Specific Checks

| Format | Profile command | Red flags |
|--------|----------------|-----------|
| CSV/TSV | `head -1 \| tr ',' '\n'`, `wc -l`, sample rows | HTML in first line, single column (wrong delimiter), row count < 10 |
| JSON | `python3 -c "import json; d=json.load(open('f.json')); print(type(d).__name__, len(d) if isinstance(d,list) else list(d.keys())[:10])"` | Empty array, single-key wrapper hiding real data, nested too deep |
| Parquet | `python3 -c "import pyarrow.parquet as pq; s=pq.read_schema('f.parquet'); print(s)"` | Zero row groups, unexpected column types |
| ZIP | `unzip -l f.zip \| tail -20`, check for data files vs just docs | Only contains PDFs/codebooks, no actual data files |
| Excel | `python3 -c "import openpyxl; wb=openpyxl.load_workbook('f.xlsx'); print(wb.sheetnames)"` | Single sheet with instructions, merged cells |
| VCF | `grep -c '^#' f.vcf`, `grep -v '^#' f.vcf \| wc -l`, `grep '^#CHROM' f.vcf` | Zero variants, missing header, wrong genome build |

### What to Output

After profiling, state concisely:
- **Format:** CSV, 14 columns, tab-delimited
- **Size:** 2.3 MB, 45,218 rows
- **Schema:** [list key columns and types]
- **Quality notes:** 3 columns have >10% nulls, dates in MM/DD/YYYY format, IDs look like FIPS codes
- **Join keys:** `state_fips` matches census data, `ticker` matches entity universe

If the profile reveals the download is garbage (HTML trap, truncated, wrong format), say so immediately and re-download or try a different approach. Don't wire bad data into anything.
