---
name: code-review
description: Continuous code review via free CLI models. Runs scout (Gemini/Codex CLI), validates findings against actual code, implements safe fixes. Designed for `/loop` — each invocation auto-rotates project and focus.
user-invocable: true
argument-hint: '[project focus] — e.g., "intel optimization", "genomics dead-code", or blank for auto-rotation'
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Agent
---

# Continuous Code Review

Run the code-review scout (free Gemini/Codex CLI calls), validate findings against actual source code, implement safe fixes.

**Designed for `/loop`**: each invocation auto-picks the next (project, focus) pair from a 25-day rotation. Or pass arguments to target specific work.

## Step 1: Determine Target

```bash
SCOUT="$HOME/Projects/meta/scripts/code-review-scout.py"
SCHEDULE="$HOME/Projects/meta/scripts/code-review-schedule.py"
```

**If `$ARGUMENTS` is provided**, parse it:
- `"intel optimization"` → project=intel, focus=optimization
- `"genomics"` → project=genomics, focus=auto (next in rotation)
- `"dead-code"` → project=auto, focus=dead-code (apply to today's project)

**If no arguments**, get today's rotation assignment:
```bash
cd ~/Projects/meta && uv run python3 "$SCHEDULE" --dry-run
```

This prints the project and focus for today. Use those values.

Valid projects: `intel`, `genomics`, `meta`, `selve`, `skills`
Valid focuses: `refactoring`, `dead-code`, `optimization`, `patterns`, `security`

## Step 2: Run Scout

```bash
cd ~/Projects/meta && uv run python3 "$SCOUT" ~/Projects/$PROJECT \
  --focus $FOCUS --provider google --workers 2
```

Use `--provider google` by default (Gemini CLI, free with Pro sub). If the scout reports rate limiting, re-run with `--provider openai` (Codex CLI).

For small modules (<30 files), add `--both` to get cross-model coverage.

**Timeout:** Set Bash timeout to 600000 (10 min) — large projects have 40+ batches.

If the scout finds zero new findings, report that and stop. Don't fabricate work.

## Step 3: Read Findings

```bash
FINDINGS="$HOME/Projects/meta/artifacts/code-review/$PROJECT/$(date +%Y-%m-%d).jsonl"
```

Read the JSONL file. Count findings by severity:

```bash
cat "$FINDINGS" | uv run python3 -c "
import json, sys
from collections import Counter
lines = [json.loads(l) for l in sys.stdin if l.strip()]
today = [l for l in lines if l.get('focus') == '$FOCUS']
by_sev = Counter(l['severity'] for l in today)
print(f'Today: {len(today)} findings (HIGH: {by_sev.get(\"HIGH\",0)}, MEDIUM: {by_sev.get(\"MEDIUM\",0)}, LOW: {by_sev.get(\"LOW\",0)})')
for l in sorted(today, key=lambda x: ('HIGH','MEDIUM','LOW').index(x['severity']))[:15]:
    print(f\"  {l['severity']:6} {l['file']}:{l['line']} {l['description'][:100]}\")
"
```

If no HIGH findings, scan MEDIUMs for the high-true-positive patterns (unchecked returncode, divergent copies, code duplication) — these are often misclassified. Don't validate LOWs.

## Step 4: Validate ALL HIGH Findings

**This is the critical step. Models hallucinate code issues.**

Validate **every** HIGH finding, not a sample. Read the actual code for each one. If there are 60 HIGHs, validate 60. Batch reads in parallel to go fast.

**Do NOT categorize-then-skip.** "38 broad except findings" is not a verdict — each one lives in different code with different risk profiles. A bare except in a clinical output generator is dangerous; the same pattern in a `validate()` tool-availability check is correct. Read the code, judge individually.

### Triage by context, not by pattern name

The scout reports patterns. You judge whether the pattern matters *in that location*:

| Context | Broad except is... | Unchecked returncode is... |
|---------|--------------------|----|
| Clinical/report output | **CONFIRMED** — silent data loss | **CONFIRMED** — garbage in reports |
| External API/network call | FALSE POSITIVE — correct pattern | N/A |
| `validate()` tool checks | FALSE POSITIVE — expected | FALSE POSITIVE |
| Post-output stats gathering | FALSE POSITIVE — acceptable | **PARTIAL** — should warn |
| Checkpoint/resume loading | **PARTIAL** — should log | N/A |
| Documented design (CLAUDE.md) | FALSE POSITIVE | FALSE POSITIVE |

### Common real bugs (from observed data)

These patterns have a >50% true positive rate:
- **Unchecked `subprocess.run` returncode before parsing stdout** — silently produces garbage
- **Divergent function copies** — ranking/scoring functions duplicated across files with drift
- **Code duplication across sibling scripts** — stat helpers, loaders copy-pasted identically
- **Silent error swallowing in data-producing paths** — `except Exception: pass` where the output is consumed downstream

These patterns have a >75% false positive rate:
- "Broad except" in network calls, validate(), stats gathering, lazy imports
- "Inconsistent return type" across modal scripts (dict vs string) — style debt, not bugs
- "Missing init_stage/finalize_stage" — lifecycle gaps, not data correctness
- "Uses subprocess.run instead of run_cmd" — style inconsistency unless returncode is also unchecked

### For each finding

1. **Read the actual file** at the cited location. Line numbers are typically wrong by 30-110 lines — search for the function/pattern name instead.
2. **Determine verdict:**
   - **CONFIRMED** — the issue exists and is worth fixing
   - **PARTIAL** — issue exists but severity overstated or fix risks behavior change
   - **FALSE POSITIVE** — the code doesn't have this issue, or the pattern is correct for context
3. **For CONFIRMED findings with straightforward fixes** (<20 lines changed):
   - Implement the fix
   - Verify the script still loads: `cd ~/Projects/$PROJECT && uv run python3 -c "import sys; sys.path.insert(0,'.'); import $MODULE" 2>&1 | tail -3`
   - Commit in the target project repo with appropriate scope tag

### Commit format

Use the project's commit conventions, not a fixed format. Tag with the relevant scope:
- `[curation]` for classification/ranking logic fixes
- `[pipeline]` for subprocess handling, error propagation
- `[refactor]` for deduplication, shared module extraction

**Do NOT fix:**
- Findings that require understanding business logic you haven't read
- LIKE/fuzzy join patterns (usually deliberate for entity matching)
- Test files (side-effect tests may look like dead code)
- Issues where the fix might change behavior
- Style-only inconsistencies with no correctness impact (return type mismatches, naming conventions)

## Step 5: Report

Print a summary:

```
## Code Review: $PROJECT ($FOCUS)
- Findings: N total (H HIGH, M MEDIUM, L LOW)
- Validated: X of Y HIGH findings
- Confirmed: A, False positive: B, Partial: C
- Fixed: D changes committed
- Skipped: [reasons]
```

If running via `/loop`, this output helps the user see progress across invocations.

## Usage Examples

```
# One-shot on specific project
/code-review intel optimization

# Auto-rotation (picks today's assignment)
/code-review

# Loop every 30 minutes, auto-rotating
/loop 30m /code-review

# Target specific focus across today's project
/code-review dead-code
```

## Expected False Positive Rate

Gemini's "patterns" focus produces ~75% false positives on HIGHs (observed on genomics, 60 HIGHs → 8 confirmed, 7 partial, 45 FP). Most FPs are "broad except" in contexts where it's the correct pattern. The validation step is where value is created — the scout is a noisy signal generator.

## What This Skill Does NOT Do

- **Does not use API credits for the scout.** Gemini CLI and Codex CLI are free/subscription.
- **Does not fix everything.** Only CONFIRMED findings with straightforward fixes get committed. PARTIAL findings are reported.
- **Does not skip validation.** Every HIGH finding requires reading the actual code. Gemini fabricates line numbers ~100% of the time.
- **Does not review the same file twice.** Findings are deduplicated by content hash across runs.
- **Does not categorize-then-dismiss.** "38 broad except findings" is not a verdict. Each one gets individual assessment based on what code it's in.

$ARGUMENTS
