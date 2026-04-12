# Sweep Axes — Mechanical Check Scripts

Each axis has a set of deterministic checks that run before any model dispatch.
Copy-paste these into Bash or adapt to the project's specifics.

## config

### Dual-registry alignment

Cross-check `database_versions.json` keys against `dataset_registry.py` keys.
Naming conventions often differ — check both exact match and fuzzy match.

```python
import json, re

with open('config/database_versions.json') as f:
    dbv_keys = set(json.loads(f.read()).keys())

with open('scripts/dataset_registry.py') as f:
    content = f.read()
    reg_keys = set(re.findall(r'"([a-z_0-9]+)":\s*DatasetSpec', content))

only_dbv = sorted(dbv_keys - reg_keys)
only_reg = sorted(reg_keys - dbv_keys)

print(f'In database_versions.json only ({len(only_dbv)}):')
for k in only_dbv: print(f'  {k}')
print(f'In dataset_registry.py only ({len(only_reg)}):')
for k in only_reg: print(f'  {k}')
```

### Schema field coverage

Check if JSON entries have all fields the Pydantic model expects:

```python
# For each config JSON, read the corresponding Pydantic model in pipeline_config.py
# and check: does every JSON entry have the required fields?
# Also check: does the JSON use field names the model doesn't define?
```

### Config JSON internal consistency

For trait_panels, gene_panels, variant_registry: check that description fields
match the gene/variant they're attached to. Common failure: copy-paste from
another entry.

```python
# For each variant entry, check:
# 1. Does the description mention a gene different from the gene field?
# 2. Does the description mention a chromosome different from the chrom field?
# 3. Are gene symbols valid HGNC names (no slashes like DEC2/BHLHE41)?
```

## conventions

### JSON write function usage

```bash
echo "write_json_safe: $(grep -rl 'write_json_safe' scripts/*.py | wc -l)"
echo "write_json_atomic: $(grep -rl 'write_json_atomic' scripts/*.py | wc -l)"
echo "raw json.dump: $(grep -rn 'json\.dump(' scripts/*.py | grep -v 'write_json\|def \|#\|test_' | wc -l)"
```

### Subprocess wrapper usage

```bash
echo "run_cmd: $(grep -rl 'run_cmd(' scripts/modal_*.py | wc -l)"
echo "raw subprocess.run: $(grep -rn 'subprocess\.run(' scripts/modal_*.py | grep -v 'run_cmd\|#' | wc -l)"
```

### Import pattern compliance

Check for patterns that violate agent-script-conventions:
- `from modal_utils import write_json_safe` (should be `write_json_atomic` from `variant_evidence_core`)
- `import subprocess` in modal scripts (should use `run_cmd`)
- `json.loads(path.read_text())` for config (should use typed loaders from `pipeline_config`)

## duplication

### Hash-based divergence detection

Find functions with the same name in multiple files, then hash their bodies to
detect divergence:

```python
import re, hashlib, glob, os
from collections import defaultdict

funcs = defaultdict(list)
for f in sorted(glob.glob('scripts/modal_*.py')):
    with open(f) as fh:
        content = fh.read()
    for m in re.finditer(r'^def (\w+)\([^)]*\).*?(?=\ndef |\Z)', content, re.DOTALL | re.MULTILINE):
        name = m.group(1)
        if not name.startswith('_'):
            body = m.group(0).strip()
            h = hashlib.md5(body.encode()).hexdigest()[:8]
            funcs[name].append((os.path.basename(f), h, len(body.split('\n'))))

# Report functions in 3+ files, or 2+ files with different hashes
for name, locations in sorted(funcs.items(), key=lambda x: -len(x[1])):
    hashes = set(h for _, h, _ in locations)
    if len(locations) >= 3 or (len(locations) >= 2 and len(hashes) > 1):
        status = 'DIVERGED' if len(hashes) > 1 else 'IDENTICAL'
        print(f'{name}: {status} ({len(locations)} files, {len(hashes)} variants)')
        for fname, h, lines in locations[:5]:
            print(f'  {fname}: {h} ({lines} lines)')
```

## registration

### Stage registration completeness

```python
import re, glob, os

with open('scripts/pipeline_stages.py') as f:
    content = f.read()

stage_names = set(re.findall(r'name="([^"]+)"', content))
script_refs = set(re.findall(r'script="([^"]+)"', content))

modal_scripts = glob.glob('scripts/modal_*.py')
# Exclude known non-stage scripts
NON_STAGE = {'modal_utils', 'modal_sync_results', 'modal_controller',
             'modal_watchdog', 'modal_probe', 'modal_cost_report',
             'modal_genomics', 'modal_benchmark_score', 'modal_db_download',
             'modal_db_sync', 'modal_db_exomiser', 'modal_db_exomiser_extras',
             'modal_download_results', 'modal_download_mobideep',
             'modal_download_mobideep_parallel', 'modal_download_spliceai_scores',
             'modal_upload_cram', 'modal_upload_new_datasets',
             'modal_setup_sample_dirs', 'modal_watch_results',
             'modal_migrate_volume', 'modal_import_probe',
             'modal_giab_download', 'modal_giab_happy', 'modal_giab_validate',
             'modal_local_stage_runner', 'modal_acquire_nealelab',
             'modal_reference_download'}

for s in modal_scripts:
    base = os.path.basename(s).replace('.py', '')
    if base not in NON_STAGE:
        stage = base.replace('modal_', '')
        if stage not in stage_names:
            print(f'UNREGISTERED: {base}.py (expected stage name: {stage})')

# Check script references point to existing files
for ref in sorted(script_refs):
    if not os.path.exists(f'scripts/{ref}'):
        print(f'MISSING SCRIPT: {ref}')
```

## lifecycle

### @stage decorator adoption

```bash
# Stage scripts with @stage
grep -l '@stage' scripts/modal_*.py | wc -l
# Stage scripts without @stage (excluding non-stage utilities)
grep -rL '@stage' scripts/modal_*.py | grep -v 'modal_utils\|modal_controller\|...' | wc -l
```

### init_stage / finalize_stage consistency

```bash
# @stage with init_stage
comm -12 <(grep -l '@stage' scripts/modal_*.py | sort) <(grep -l 'init_stage' scripts/modal_*.py | sort) | wc -l
# @stage WITHOUT init_stage
comm -23 <(grep -l '@stage' scripts/modal_*.py | sort) <(grep -l 'init_stage' scripts/modal_*.py | sort)
# init_stage WITHOUT finalize_stage (should be zero)
comm -23 <(grep -l 'init_stage' scripts/modal_*.py | sort) <(grep -l 'finalize_stage' scripts/modal_*.py | sort)
```

## ir

### Payload/adapter coverage (requires Flash)

This axis is best handled by Flash because the relationships are semantic, not
mechanical. Send:
- `finding_ir.py` (full — defines all payload types)
- `finding_adapters.py` (first + last 500 lines)
- `finding_adapters_pgx.py` (full)
- `finding_assembly.py` (full)
- `finding_policy.py` (full)
- `case_bundle_builder.py` (first 100 lines)

Flash prompt: see `flash-prompts.md` § IR Consistency.

## paths

### Paths() class adoption

```bash
echo "Paths() users: $(grep -l 'from wgs_config import.*Paths\|Paths()' scripts/modal_*.py | wc -l)"
echo "DATA_DIR users: $(grep -l 'DATA_DIR' scripts/modal_*.py | wc -l)"
echo "f-string /data/ (ad-hoc): $(grep -l 'f\"/data/' scripts/modal_*.py | wc -l)"
```

### stage_artifact() vs manual path construction

```bash
echo "stage_artifact() users: $(grep -l 'stage_artifact(' scripts/modal_*.py | wc -l)"
echo "Manual results/ f-strings: $(grep 'results/' scripts/modal_*.py | grep -v 'stage_artifact\|#\|import\|doc' | grep 'f"' | wc -l)"
```
