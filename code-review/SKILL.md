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

If no HIGH findings, report the MEDIUM summary and stop. Don't validate LOWs.

## Step 4: Validate HIGH Findings

**This is the critical step. Models hallucinate code issues.**

For each HIGH finding (up to 10 per invocation):

1. **Read the actual file** at the cited location. Line numbers are typically wrong by 30-110 lines — search for the function/pattern name instead.
2. **Determine verdict:**
   - **CONFIRMED** — the issue exists and is worth fixing
   - **PARTIAL** — issue exists but line is wrong or severity overstated
   - **FALSE POSITIVE** — the code doesn't have this issue
3. **For CONFIRMED findings with straightforward fixes** (<20 lines changed):
   - Implement the fix
   - Verify the script still loads: `cd ~/Projects/$PROJECT && uv run python3 $FILE --help 2>/dev/null || uv run python3 -c "import importlib.util; s=importlib.util.spec_from_file_location('m','$FILE'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)" 2>&1 | tail -3`
   - Commit in the target project repo: `[perf] Fix: description — code-review finding`

**Do NOT fix:**
- Findings that require understanding business logic you haven't read
- LIKE/fuzzy join patterns (usually deliberate for entity matching)
- Test files (side-effect tests may look like dead code)
- Issues where the fix might change behavior

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

## What This Skill Does NOT Do

- **Does not use API credits for the scout.** Gemini CLI and Codex CLI are free/subscription.
- **Does not fix everything.** Only straightforward HIGH findings get implemented. The rest are logged for manual review.
- **Does not skip validation.** Every fix requires reading the actual code first. Gemini fabricates line numbers ~100% of the time.
- **Does not review the same file twice.** Findings are deduplicated by content hash across runs.

$ARGUMENTS
