---
name: code-review
description: "Use when: /code-review, review diff/PR/change, scout loop. Composer default scout; validates against code. NOT plan/findings review (/critique)."
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
effort: medium
---

# Continuous Code Review

Run the code-review scout (local CLI — **Cursor Composer 2.5** default via `cursor-agent`),
validate findings against actual source code, implement safe fixes.

**Not the Claude Code vendor `/code-review` plugin** — this is our local skill + scout scripts
in `agent-infra/scripts/`. Critique/execute closeouts call this skill.

**Designed for `/loop`**: each invocation auto-picks the next (project, focus) pair from a 25-day
rotation. Or pass arguments to target specific work.

## Step 1: Determine Target

```bash
SCOUT="$HOME/Projects/agent-infra/scripts/code-review-scout.py"
SCHEDULE="$HOME/Projects/agent-infra/scripts/code-review-schedule.py"
```

**If `$ARGUMENTS` is provided**, parse it:
- `"intel optimization"` → project=intel, focus=optimization
- `"genomics"` → project=genomics, focus=auto (next in rotation)
- `"dead-code"` → project=auto, focus=dead-code (apply to today's project)

**If no arguments**, get today's rotation assignment:
```bash
uv run python3 "$SCHEDULE" --dry-run
```

Valid projects: `intel`, `genomics`, `agent-infra`, `phenome`, `skills`, `hutter`
Valid focuses: `refactoring`, `dead-code`, `optimization`, `patterns`, `security`

## Step 2: Run Scout

```bash
cd ~/Projects/agent-infra && uv run python3 "$SCOUT" ~/Projects/$PROJECT \
  --focus $FOCUS --provider cursor --workers 2
```

**Provider order (local-first):**
1. **`cursor`** (default) — `composer-2.5` via `cursor-agent` / llmx cursor transport.
   Frontier-equal on injected-defect review; tight output contract required.
2. **`google`** — Gemini via llmx (paid API path since 2026-05-31). Use on Cursor pool exhaustion.
3. **`openai`** — GPT-5.5 via codex-cli. Fallback when Gemini rate-limits.

If the scout reports rate limiting on cursor, re-run with `--provider google` or `--provider openai`.
For small modules (<30 files), add `--all-providers` for cross-model coverage.

**Timeout:** Set Bash timeout to 600000 (10 min) — large projects have 40+ batches.

If the scout finds zero new findings, report that and stop. Don't fabricate work.

## Step 3: Read Findings

```bash
FINDINGS="$HOME/Projects/agent-infra/artifacts/code-review/$PROJECT/$(date +%Y-%m-%d).jsonl"
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

If no HIGH findings, scan MEDIUMs for the high-true-positive patterns (unchecked returncode,
divergent copies, code duplication) — these are often misclassified. Don't validate LOWs.

## Step 4: Validate ALL HIGH Findings

**This is the critical step. Models hallucinate code issues.**

Validate **every** HIGH finding, not a sample. Read the actual code for each one.

**Do NOT categorize-then-skip.** Read the code, judge individually.

**Skip anything tooling already enforces** (linter, type-checker, formatter) — those are caught for free;
review for what tools can't see. A finding a `ruff`/`pyright` run would flag is noise here.

### Triage by context, not by pattern name

| Context | Broad except is... | Unchecked returncode is... |
|---------|--------------------|----|
| Clinical/report output | **CONFIRMED** — silent data loss | **CONFIRMED** — garbage in reports |
| External API/network call | FALSE POSITIVE — correct pattern | N/A |
| `validate()` tool checks | FALSE POSITIVE — expected | FALSE POSITIVE |
| Post-output stats gathering | FALSE POSITIVE — acceptable | **PARTIAL** — should warn |

### For each finding

1. **Read the actual file** at the cited location. Line numbers are often wrong — search for the pattern.
2. **Verdict:** CONFIRMED / PARTIAL / FALSE POSITIVE
3. **CONFIRMED + straightforward fix (<20 lines):** fix, verify import/load, commit in target repo.

**Do NOT fix:** business-logic you haven't read, deliberate fuzzy joins, test side-effects, behavior-changing fixes.

## Step 5: Report

```
## Code Review: $PROJECT ($FOCUS)
- Findings: N total (H HIGH, M MEDIUM, L LOW)
- Validated: X of Y HIGH findings
- Confirmed: A, False positive: B, Partial: C
- Fixed: D changes committed
```

### Artifact Output

```bash
mkdir -p ~/.claude/artifacts/$PROJECT
```

Write `~/.claude/artifacts/$PROJECT/code-review-$(date +%Y-%m-%d).json` with confirmed/unfixed summary
for downstream skills (`/upgrade`, `/critique close`).

## Module-depth lens (design-level findings)

Beyond line-level smells, flag shallow / over-abstracted design — vocabulary from Ousterhout/Feathers
(see `agent-infra/research/2026-06-19-mattpocock-skills-best-ideas.md`):

- **Shallow module** — an interface nearly as complex as its implementation (a thin pass-through adding
  no leverage). Fix is depth, not more wrappers. **Depth = leverage at the interface**, not a line ratio.
- **Hypothetical seam** — a port/interface with a **single** implementation is needless indirection.
  Rule: *one adapter = hypothetical seam, two = real* (= our proven-common-≥2). Flag single-adapter ports.
- **Deletion test** — if this module/abstraction were deleted, what actually breaks? If little, it isn't
  pulling weight (a dead-code / over-abstraction finding).
- **Tests past the interface** — a test that asserts internal state (must change whenever the
  implementation changes) instead of observable behavior. The interface is the test surface.

## Depth presets (for critique/execute callers)

| Preset | Scout focus | Provider | Notes |
|--------|-------------|----------|-------|
| `low` | patterns | cursor | Per-phase gate; ≤4 findings target |
| `high` | security + patterns | cursor + `--all-providers` on diff scope | Slice closeout; recall mode |

For **diff-scoped** review (plan closeout), pass only changed files via `--module` or a hand-built
context packet — don't scan the whole repo. **Fail fast: confirm the ref resolves (`git rev-parse`)
and the diff is non-empty BEFORE spawning scouts** — a bad ref or empty diff should fail here, not
inside N parallel workers.

## Usage Examples

```
/code-review intel optimization    # one-shot
/code-review                       # auto-rotation
/loop 30m /code-review             # continuous rotation
```

## What This Skill Does NOT Do

- **Does not use the Claude Code vendor code-review plugin** — local scouts only.
- **Does not skip validation** — every HIGH requires reading actual code.
- **Does not fix everything** — only CONFIRMED straightforward fixes get committed.

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-14] Diff-scoped module dry-run silently omitted oversized changed files direct_table_online.py and test_direct_table_online.py while reporting success; scout must list/fail-loud on skipped files or chunk them.**
